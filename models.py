from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from database import Base

class Conteudo(Base):
    __tablename__ = "conteudos"

    #Estrutura das tabelas
    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String, nullable=False)          # "noticia" ou "edital"
    titulo = Column(String, nullable=False)
    texto_original = Column(Text, nullable=False)
    resumo = Column(Text, nullable=True)            # preenchido depois, pela IA
    imagem_url = Column(String, nullable=True)
    url_origem = Column(String, unique=True, nullable=False)  # evita duplicar
    origem = Column(String, nullable=False)          # "scraper" ou "manual"
    status = Column(String, default="ativo")         # "ativo", "expirado", "oculto"
    data_publicacao = Column(DateTime, default=datetime.utcnow)
    data_expiracao = Column(DateTime, nullable=True) # usado principalmente por editais  

    #Column(...): define um campo/coluna da tabela e seu tipo (texto, número, data...). 
    #nullable=False: esse campo é obrigatório, não pode ficar vazio.
    #nullable=True: esse campo é opcional.
    #unique=True no url_origem: garante que o banco recusa duplicar a mesma URL — é assim que evitamos reprocessar a mesma notícia duas vezes. 
    #primary_key=True: o id é o identificador único de cada linha (o banco preenche sozinho, incrementando: 1, 2, 3...).  
     
class ConfigTV(Base):
    __tablename__ = "config_tv"

    id = Column(Integer, primary_key=True, index=True)
    modo_atual = Column(String, nullable=False, default="geral")  # "geral" ou "edital"
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) # onupdate=datetime.utcnow faz o campo atualizado_em se atualizar sozinho toda vez que a linha for modificada (não só na criação) 

    