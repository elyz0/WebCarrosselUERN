import json
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_PATH = LOG_DIR / "execucoes.jsonl"


def registrar_execucao(tipo: str, inicio: datetime, resultado=None, erro: str | None = None):
    """Grava uma execução concluída em formato JSONL, sem interromper o fluxo principal."""
    fim = datetime.now().astimezone()
    evento = {
        "tipo": tipo,
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "duracao_segundos": round((fim - inicio).total_seconds(), 2),
        "status": "falha" if erro else "ok",
        "erro": erro,
        "resultado": resultado or {},
    }
    try:
        LOG_DIR.mkdir(exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as arquivo:
            arquivo.write(json.dumps(evento, ensure_ascii=False) + "\n")
    except OSError:
        pass


def resumo_do_dia(data: str | None = None) -> dict:
    """Retorna a situação das duas execuções esperadas de cada rotina no dia."""
    hoje = data or datetime.now().astimezone().date().isoformat()
    execucoes = []
    if LOG_PATH.exists():
        try:
            with LOG_PATH.open(encoding="utf-8") as arquivo:
                for linha in arquivo:
                    try:
                        evento = json.loads(linha)
                    except json.JSONDecodeError:
                        continue
                    if evento.get("inicio", "")[:10] == hoje:
                        execucoes.append(evento)
        except OSError:
            pass

    resultado = {}
    for tipo in ("scraper", "resumir"):
        eventos = [evento for evento in execucoes if evento.get("tipo") == tipo]
        concluidas = [evento for evento in eventos if evento.get("status") == "ok"]
        tokens = {
            "entrada": sum(evento.get("resultado", {}).get("tokens", {}).get("entrada", 0) or 0 for evento in eventos),
            "saida": sum(evento.get("resultado", {}).get("tokens", {}).get("saida", 0) or 0 for evento in eventos),
            "pensamento": sum(evento.get("resultado", {}).get("tokens", {}).get("pensamento", 0) or 0 for evento in eventos),
            "total": sum(evento.get("resultado", {}).get("tokens", {}).get("total", 0) or 0 for evento in eventos),
        }
        resultado[tipo] = {
            "esperadas": 2,
            "execucoes": len(eventos),
            "concluidas": len(concluidas),
            "falhas": len(eventos) - len(concluidas),
            "faltantes": max(0, 2 - len(concluidas)),
            "tokens": tokens,
        }
    return {"data": hoje, "rotinas": resultado, "ultimas_execucoes": execucoes[-10:]}
