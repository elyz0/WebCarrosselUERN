import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime

from sqlalchemy.orm import Session

import models

# Chave lida do ambiente. Nunca deixe a chave escrita no código.
# No Linux/Mac:  export GEMINI_API_KEY="sua_chave_aqui"
# Pegue a chave em: https://aistudio.google.com/apikey
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"  # bom equilíbrio entre custo zero e qualidade
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
    "type": "object",
    "properties": {
        "resumo": {
            "type": "string",
            "description": "Resumo pronto para exibição no carrossel.",
        },
        "data_expiracao": {
            "type": ["string", "null"],
            "format": "date",
            "description": "Data final do edital em AAAA-MM-DD, ou null.",
        },
    },
    "required": ["resumo", "data_expiracao"],
    "additionalProperties": False,
}


class ErroResumo(Exception):
    pass


def _chamar_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise ErroResumo("GEMINI_API_KEY não configurada no ambiente.")

    corpo = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 200,
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
            return texto
        except urllib.error.HTTPError as erro:
            corpo_erro = erro.read().decode("utf-8", errors="ignore")
            ultimo_erro = f"HTTP {erro.code}: {corpo_erro[:300]}"
            if erro.code == 429:
                # limite de requisições por minuto/dia atingido: espera mais e tenta de novo
                time.sleep(15 * tentativa)
                continue
            if erro.code >= 500:
                time.sleep(3 * tentativa)
                continue
            break  # erro 4xx que não é rate limit não adianta repetir
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as erro:
            ultimo_erro = str(erro)
            time.sleep(3 * tentativa)

    raise ErroResumo(ultimo_erro or "Falha desconhecida ao chamar a API do Gemini.")


def resumir_texto(tipo: str, titulo: str, texto: str) -> tuple[str, datetime | None]:
    texto_limitado = texto[:6000]  # margem de segurança para não estourar tokens à toa
    prompt = PROMPT_BASE.format(tipo=tipo, titulo=titulo, texto=texto_limitado)
    try:
        resultado = json.loads(_chamar_gemini(prompt))
    except json.JSONDecodeError as erro:
        raise ErroResumo("A API não devolveu o JSON esperado.") from erro

    resumo = str(resultado.get("resumo") or "").strip()
    if not resumo:
        raise ErroResumo("A API devolveu um resumo vazio.")

    valor_data = resultado.get("data_expiracao")
    if valor_data is None:
        return resumo, None
    if not isinstance(valor_data, str):
        raise ErroResumo("A data de expiração devolvida pela API é inválida.")
    try:
        return resumo, datetime.strptime(valor_data, "%Y-%m-%d")
    except ValueError as erro:
        raise ErroResumo("A data de expiração devolvida pela API é inválida.") from erro


def resumir_pendentes(db: Session, limite: int = 20) -> dict:
    """Busca itens sem resumo no banco, gera o resumo via Gemini e salva."""
    pendentes = (
        db.query(models.Conteudo)
        .filter(models.Conteudo.resumo.is_(None))
        .filter(models.Conteudo.status == "ativo")
        .order_by(models.Conteudo.data_publicacao.desc())
        .limit(limite)
        .all()
    )

    totais = {"resumidos": 0, "falhas": 0, "detalhes": []}

    for item in pendentes:
        try:
            resumo, data_expiracao = resumir_texto(item.tipo, item.titulo, item.texto_original)
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
