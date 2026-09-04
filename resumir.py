import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime
from datetime import timezone

from sqlalchemy.orm import Session
from dotenv import load_dotenv

import models
from observabilidade import registrar_execucao

load_dotenv()

# Chave lida do ambiente. Nunca deixe a chave escrita no código.
# No Linux/Mac:  export GEMINI_API_KEY="sua_chave_aqui"
# Pegue a chave em: https://aistudio.google.com/apikey
GEMINI_API_KEY = "".join(os.environ.get("GEMINI_API_KEY", "").split())
GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)

TIMEOUT_S = 30
MAX_TENTATIVAS = 3
PAUSA_ENTRE_ITENS_S = 4  # respeita o limite de 15 requisições/min do free tier

PROMPT_BASE = (
    "Você resume textos institucionais de uma universidade pública brasileira "
    "(UERN) para exibição em um carrossel/painel informativo e extrai a "
    "data final de vigência quando houver.\n"
    "Regras:\n"
    "- Escreva em português do Brasil, tom claro e direto.\n"
    "- Máximo de 3 frases ou 60 palavras.\n"
    "- Se for edital/concurso, priorize: o que é, prazo/data-limite e quem pode participar.\n"
    "- Se for notícia, priorize: o fato principal e por que importa.\n"
    "- Não invente datas, números ou informações que não estejam no texto.\n"
    "- Não use markdown, emojis ou aspas no resumo.\n"
    "- Em data_expiracao, informe somente a data final explícita para inscrição, "
    "submissão, vigência ou participação no edital. Não use data de publicação, "
    "data de evento ou prazo intermediário.\n"
    "- Converta data_expiracao para AAAA-MM-DD. Se não houver uma data final "
    "inequívoca, use null. Para notícias, use sempre null.\n\n"
    "Tipo do conteúdo: {tipo}\n"
    "Título: {titulo}\n"
    "Texto original:\n{texto}"
)

SCHEMA_RESPOSTA = {
    "type": "OBJECT",
    "properties": {
        "resumo": {
            "type": "STRING",
            "description": "Resumo pronto para exibição no carrossel.",
        },
        "data_expiracao": {
            "type": "STRING",
            "nullable": True,
            "format": "date",
            "description": "Data final do edital em AAAA-MM-DD, ou null.",
        },
    },
    "required": ["resumo", "data_expiracao"],
}


class ErroResumo(Exception):
    pass


def _chamar_gemini(prompt: str) -> tuple[str, dict]:
    if not GEMINI_API_KEY:
        raise ErroResumo("GEMINI_API_KEY não configurada no ambiente.")

    corpo = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 1024,
            "responseMimeType": "application/json",
            "responseSchema": SCHEMA_RESPOSTA,
        },
    }).encode("utf-8")

    pedido = urllib.request.Request(
        GEMINI_URL,
        data=corpo,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    ultimo_erro = None
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            with urllib.request.urlopen(pedido, timeout=TIMEOUT_S) as resposta:
                dados = json.loads(resposta.read().decode("utf-8"))
            candidatos = dados.get("candidates") or []
            if not candidatos:
                raise ErroResumo("Resposta da API sem candidatos (possível bloqueio de conteúdo).")
            partes = candidatos[0].get("content", {}).get("parts", [])
            texto = "".join(p.get("text", "") for p in partes).strip()
            if not texto:
                raise ErroResumo("Resposta da API veio vazia.")
            uso = dados.get("usageMetadata") or {}
            entrada = uso.get("promptTokenCount", 0) or 0
            saida = uso.get("candidatesTokenCount", 0) or 0
            pensamento = uso.get("thoughtsTokenCount", 0) or 0
            total = uso.get("totalTokenCount", entrada + saida + pensamento) or 0
            return texto, {
                "entrada": entrada,
                "saida": saida,
                "pensamento": pensamento,
                "total": total,
            }
        except urllib.error.HTTPError as erro:
            corpo_erro = erro.read().decode("utf-8", errors="ignore")
            ultimo_erro = f"HTTP {erro.code}: {corpo_erro[:2000]}"
            if erro.code == 429:
                # A API informa a cota no corpo da resposta. Não repetir um lote
                # inteiro quando a conta está sem cota diária/plano configurado.
                break
            if erro.code >= 500:
                time.sleep(3 * tentativa)
                continue
            break  # erro 4xx que não é rate limit não adianta repetir
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as erro:
            ultimo_erro = str(erro)
            time.sleep(3 * tentativa)

    raise ErroResumo(ultimo_erro or "Falha desconhecida ao chamar a API do Gemini.")


def resumir_texto(tipo: str, titulo: str, texto: str) -> tuple[str, datetime | None]:
    resumo, data_expiracao, _ = _resumir_texto_com_uso(tipo, titulo, texto)
    return resumo, data_expiracao


def _resumir_texto_com_uso(tipo: str, titulo: str, texto: str) -> tuple[str, datetime | None, dict]:
    texto_limitado = texto[:6000]  # margem de segurança para não estourar tokens à toa
    prompt = PROMPT_BASE.format(tipo=tipo, titulo=titulo, texto=texto_limitado)
    resposta_bruta, tokens = _chamar_gemini(prompt)
    print("DEBUG resposta bruta:", repr(resposta_bruta))
    try:
        resultado = json.loads(resposta_bruta)
    except json.JSONDecodeError as erro:
        raise ErroResumo("A API não devolveu o JSON esperado.") from erro

    resumo = str(resultado.get("resumo") or "").strip()
    if not resumo:
        raise ErroResumo("A API devolveu um resumo vazio.")

    valor_data = resultado.get("data_expiracao")
    if valor_data is None:
        return resumo, None, tokens
    if not isinstance(valor_data, str):
        raise ErroResumo("A data de expiração devolvida pela API é inválida.")
    try:
        return resumo, datetime.strptime(valor_data, "%Y-%m-%d"), tokens
    except ValueError as erro:
        raise ErroResumo("A data de expiração devolvida pela API é inválida.") from erro


def resumir_pendentes(db: Session, limite: int = 20) -> dict:
    """Busca itens sem resumo no banco, gera o resumo via Gemini e salva."""
    inicio = datetime.now(timezone.utc).astimezone()
    pendentes = (
        db.query(models.Conteudo)
        .filter(models.Conteudo.resumo.is_(None))
        .filter(models.Conteudo.status == "ativo")
        .order_by(models.Conteudo.data_publicacao.desc())
        .limit(limite)
        .all()
    )

    totais = {
        "pendentes": len(pendentes),
        "resumidos": 0,
        "falhas": 0,
        "detalhes": [],
        "tokens": {"entrada": 0, "saida": 0, "pensamento": 0, "total": 0},
    }

    for item in pendentes:
        try:
            resumo, data_expiracao, tokens = _resumir_texto_com_uso(
                item.tipo, item.titulo, item.texto_original
            )
            for nome, valor in tokens.items():
                totais["tokens"][nome] += valor
            item.resumo = resumo
            if item.tipo == "edital" and item.data_expiracao is None:
                item.data_expiracao = data_expiracao
            db.commit()
            totais["resumidos"] += 1
            totais["detalhes"].append({"id": item.id, "titulo": item.titulo, "ok": True})
        except ErroResumo as erro:
            db.rollback()
            totais["falhas"] += 1
            totais["detalhes"].append({"id": item.id, "titulo": item.titulo, "ok": False, "erro": str(erro)})

        time.sleep(PAUSA_ENTRE_ITENS_S)

    registrar_execucao("resumir", inicio, totais, "Itens com falha" if totais["falhas"] else None)
    return totais


if __name__ == "__main__":
    # Execução manual: python resumir.py
    # Espera que exista uma função/sessão de banco equivalente à usada no scraper.
    from database import SessionLocal  # ajuste para o nome real do seu módulo de sessão

    sessao = SessionLocal()
    try:
        resultado = resumir_pendentes(sessao)
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
    finally:
        sessao.close()
