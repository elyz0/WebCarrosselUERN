import json
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models

USER_AGENT = "WebCarrossel-UERN/1.0 (carrossel institucional; +https://portal.uern.br)"
TIMEOUT_RSS_S = 45
TIMEOUT_REST_S = 25
DIAS_NOTICIAS = 7

# WordPress: /feed na categoria. O feed de /proeg/editais/ costuma falhar (500),
# então editais entram pela categoria "Concursos e seleções" do portal.
FONTES = [
    {
        "nome": "Notícias",
        "rss": "https://portal.uern.br/blog/category/noticias/feed/",
        "rest": "https://portal.uern.br/wp-json/wp/v2/posts?categories=35&per_page=10",
        "tipo": "noticia",
    },
    {
        "nome": "Concursos e seleções",
        "rss": "https://portal.uern.br/blog/category/concursos-e-selecoes/feed/",
        "rest": "https://portal.uern.br/wp-json/wp/v2/posts?categories=3516&per_page=10",
        "tipo": "edital",
    },
]


class ExtratorHtml(HTMLParser):
    def __init__(self):
        super().__init__()
        self._pular = False
        self.partes = []
        self.imagens = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self._pular = True
        if tag == "img":
            src = dict(attrs).get("src")
            if src:
                self.imagens.append(src.strip())

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self._pular = False

    def handle_data(self, data):
        if not self._pular:
            self.partes.append(data)


def _nome_tag(elemento):
    return elemento.tag.split("}", 1)[-1]


def _filho(elemento, nome):
    for filho in elemento:
        if _nome_tag(filho) == nome:
            return filho
    return None


def _filhos(elemento, nome):
    return [filho for filho in elemento if _nome_tag(filho) == nome]


def _texto(elemento):
    if elemento is None or elemento.text is None:
        return ""
    return unescape(elemento.text).strip()


def extrair_texto_e_imagem(html):
    if not html:
        return "", None

    extrator = ExtratorHtml()
    try:
        extrator.feed(html)
        extrator.close()
    except Exception:
        texto = re.sub(r"<[^>]+>", " ", html)
        return re.sub(r"\s+", " ", unescape(texto)).strip(), None

    texto = re.sub(r"\s+", " ", unescape("".join(extrator.partes))).strip()
    imagem = None
    for url in extrator.imagens:
        if url.startswith("data:"):
            continue
        if "wp-content/uploads" in url:
            imagem = url
            break
        if imagem is None:
            imagem = url
    return texto, imagem


def inferir_tipo(titulo, categorias, tipo_padrao):
    junto = f"{titulo} {' '.join(categorias)}".lower()
    if "edital" in junto or "concurso" in junto or "seleção simplificada" in junto:
        return "edital"
    return tipo_padrao


def _parse_pubdate(valor):
    if not valor:
        return datetime.utcnow()
    try:
        data = parsedate_to_datetime(valor)
        if data.tzinfo is not None:
            data = data.astimezone(timezone.utc).replace(tzinfo=None)
        return data
    except (TypeError, ValueError, IndexError):
        pass
    try:
        iso = valor.replace("Z", "+00:00")
        data = datetime.fromisoformat(iso)
        if data.tzinfo is not None:
            data = data.astimezone(timezone.utc).replace(tzinfo=None)
        return data
    except ValueError:
        return datetime.utcnow()


def _baixar(url, timeout):
    pedido = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urlopen(pedido, timeout=timeout) as resposta:
        return resposta.read()


def _itens_do_rss(xml_bytes, tipo_padrao):
    raiz = ElementTree.fromstring(xml_bytes)
    canal = _filho(raiz, "channel")
    origem = canal if canal is not None else raiz
    itens = []

    for item in _filhos(origem, "item"):
        titulo = _texto(_filho(item, "title"))
        link = _texto(_filho(item, "link"))
        if not link:
            guid = _filho(item, "guid")
            link = _texto(guid)
        if not titulo or not link:
            continue

        encoded = _filho(item, "encoded")
        descricao = _filho(item, "description")
        html = _texto(encoded) or _texto(descricao)
        texto, imagem = extrair_texto_e_imagem(html)

        if imagem is None:
            for media in list(item):
                if _nome_tag(media) in {"content", "thumbnail"}:
                    url_media = media.attrib.get("url")
                    if url_media:
                        imagem = url_media
                        break
            enclosure = _filho(item, "enclosure")
            if imagem is None and enclosure is not None:
                tipo_midia = enclosure.attrib.get("type", "")
                if tipo_midia.startswith("image/"):
                    imagem = enclosure.attrib.get("url")

        categorias = [_texto(cat) for cat in _filhos(item, "category") if _texto(cat)]
        itens.append({
            "titulo": titulo,
            "url_origem": link.strip(),
            "texto_original": texto or titulo,
            "imagem_url": imagem,
            "tipo": inferir_tipo(titulo, categorias, tipo_padrao),
            "data_publicacao": _parse_pubdate(_texto(_filho(item, "pubDate"))),
        })
    return itens


def _itens_do_rest(corpo_bytes, tipo_padrao):
    posts = json.loads(corpo_bytes.decode("utf-8"))
    if not isinstance(posts, list):
        return []

    itens = []
    for post in posts:
        titulo_obj = post.get("title") or {}
        titulo = unescape(titulo_obj.get("rendered") or "").strip()
        link = (post.get("link") or "").strip()
        if not titulo or not link:
            continue

        html = (post.get("content") or {}).get("rendered") or ""
        if not html:
            html = (post.get("excerpt") or {}).get("rendered") or ""
        texto, imagem = extrair_texto_e_imagem(html)

        itens.append({
            "titulo": titulo,
            "url_origem": link,
            "texto_original": texto or titulo,
            "imagem_url": imagem,
            "tipo": inferir_tipo(titulo, [], tipo_padrao),
            "data_publicacao": _parse_pubdate(post.get("date") or post.get("date_gmt") or ""),
        })
    return itens


def coletar_fonte(fonte):
    """Lê o RSS; se o feed atrasar ou falhar, cai no wp-json da mesma categoria."""
    try:
        xml_bytes = _baixar(fonte["rss"], TIMEOUT_RSS_S)
        itens = _itens_do_rss(xml_bytes, fonte["tipo"])
        if itens:
            return itens, "rss"
    except (HTTPError, URLError, TimeoutError, ElementTree.ParseError, OSError):
        pass

    json_bytes = _baixar(fonte["rest"], TIMEOUT_REST_S)
    return _itens_do_rest(json_bytes, fonte["tipo"]), "rest"


def manter_itens_validos(itens: list[dict]) -> list[dict]:
    """Mantém notícias recentes; editais não expiram pela data de publicação."""
    agora = datetime.now(timezone.utc).replace(tzinfo=None)
    limite_noticias = agora - timedelta(days=DIAS_NOTICIAS)
    return [
        item
        for item in itens
        if item["tipo"] != "noticia" or item["data_publicacao"] >= limite_noticias
    ]


def _ja_existe(db: Session, url_origem: str) -> bool:
    return db.query(models.Conteudo.id).filter(models.Conteudo.url_origem == url_origem).first() is not None


def salvar_item(db: Session, item: dict) -> str:
    if _ja_existe(db, item["url_origem"]):
        return "ignorado"

    novo = models.Conteudo(
        tipo=item["tipo"],
        titulo=item["titulo"],
        texto_original=item["texto_original"],
        resumo=None,
        imagem_url=item["imagem_url"],
        url_origem=item["url_origem"],
        origem="scraper",
        status="ativo",
        data_publicacao=item["data_publicacao"],
    )
    db.add(novo)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return "ignorado"
    return "novo"


def sincronizar(db: Session) -> dict:
    totais = {"novos": 0, "ignorados": 0, "fontes": []}

    for fonte in FONTES:
        resultado = {
            "nome": fonte["nome"],
            "url": fonte["rss"],
            "via": None,
            "novos": 0,
            "ignorados": 0,
            "erro": None,
        }
        try:
            itens, via = coletar_fonte(fonte)
            resultado["via"] = via
            itens = manter_itens_validos(itens)
            for item in itens:
                if salvar_item(db, item) == "novo":
                    resultado["novos"] += 1
                else:
                    resultado["ignorados"] += 1
        except Exception as erro:
            db.rollback()
            resultado["erro"] = str(erro)

        totais["novos"] += resultado["novos"]
        totais["ignorados"] += resultado["ignorados"]
        totais["fontes"].append(resultado)

    return totais
