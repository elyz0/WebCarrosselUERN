from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# Formato pra CRIAR um conteúdo manualmente (o que o usuário envia)
class ConteudoCreate(BaseModel):
    tipo: str                    # "noticia" ou "edital"
    titulo: str
    texto_original: str
    imagem_url: Optional[str] = None
    url_origem: Optional[str] = None   # antes: url_origem: str
    data_expiracao: Optional[datetime] = None

# Formato de RETORNO (o que a API devolve, já com id, resumo, etc.)
class ConteudoResponse(BaseModel):
    id: int
    tipo: str
    titulo: str
    texto_original: str
    resumo: Optional[str]
    imagem_url: Optional[str]
    url_origem: Optional[str]          # antes: url_origem: str
    origem: str
    status: str
    data_publicacao: datetime
    data_expiracao: Optional[datetime]

    class Config:
        from_attributes = True  # permite converter direto do objeto do SQLAlchemy 

# Para edição, onde tudo é opcional — só manda o que quer mudar
class ConteudoUpdate(BaseModel):
    titulo: Optional[str] = None
    texto_original: Optional[str] = None
    resumo: Optional[str] = None
    imagem_url: Optional[str] = None
    status: Optional[str] = None
    data_expiracao: Optional[datetime] = None 

#
class ConfigTVResponse(BaseModel):
    modo_atual: str
    atualizado_em: datetime

    class Config:
        from_attributes = True

#
class ConfigTVUpdate(BaseModel):
    modo_atual: str  # "geral" ou "edital"