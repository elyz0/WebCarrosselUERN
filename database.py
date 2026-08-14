from sqlalchemy import create_engine #engine: a conexão real com o arquivo do banco.
from sqlalchemy.orm import sessionmaker, declarative_base #uma "sessão" — é através dela que o código vai ler e escrever dados no banco, uma sessão por requisição.
#Base: uma classe base da qual todas as nossas tabelas (que ainda vamos criar) vão herdar.
 
# Isso cria (ou conecta a) um arquivo local chamado carrossel.db
DATABASE_URL = "sqlite:///./carrossel.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()