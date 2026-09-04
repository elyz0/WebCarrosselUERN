from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]


def _load_resumir_module():
    spec = importlib.util.spec_from_file_location("resumir_module", ROOT / "resumir.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_modelo_gemini_usa_versao_suportada():
    module = _load_resumir_module()
    assert module.GEMINI_MODEL.startswith("gemini-2."), (
        f"Modelo Gemini inesperado: {module.GEMINI_MODEL}"
    )


def test_frontend_nao_faz_fallback_para_texto_original():
    js = (ROOT / "frontend" / "tela" / "carrossel.js").read_text(encoding="utf-8")
    assert "item.resumo || item.texto_original" not in js
