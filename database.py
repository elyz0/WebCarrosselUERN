from sqlalchemy import create_engine, inspect, text #engine: a conexão real com o arquivo do banco.
from sqlalchemy.orm import sessionmaker, declarative_base #uma "sessão" — é através dela que o código vai ler e escrever dados no banco, uma sessão por requisição.
# Base: uma classe base da qual todas as nossas tabelas (que ainda vamos criar) vão herdar.
 
# Isso cria (ou conecta a) um arquivo local chamado carrossel.db
DATABASE_URL = "sqlite:///./carrossel.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base() 

def migrar_url_origem_opcional():
    """Atualiza bancos antigos onde url_origem ainda era obrigatoria."""
    if "conteudos" not in inspect(engine).get_table_names():
        return

    colunas = inspect(engine).get_columns("conteudos")
    url_origem = next(coluna for coluna in colunas if coluna["name"] == "url_origem")
    if url_origem["nullable"]:
        return

    with engine.begin() as conexao:
        conexao.execute(text("ALTER TABLE conteudos RENAME TO conteudos_antiga"))
        conexao.execute(text("""
            CREATE TABLE conteudos (
                id INTEGER NOT NULL PRIMARY KEY,
                tipo VARCHAR NOT NULL,
                titulo VARCHAR NOT NULL,
                texto_original TEXT NOT NULL,
                resumo TEXT,
                imagem_url VARCHAR,
                url_origem VARCHAR UNIQUE,
                origem VARCHAR NOT NULL,
                status VARCHAR,
                data_publicacao DATETIME,
                data_expiracao DATETIME
            )
        """))
        conexao.execute(text("""
            INSERT INTO conteudos
            SELECT id, tipo, titulo, texto_original, resumo, imagem_url,
                   url_origem, origem, status, data_publicacao, data_expiracao
            FROM conteudos_antiga
        """))
        conexao.execute(text("DROP TABLE conteudos_antiga"))

# Abre uma sessão do banco pra cada requisição e fecha depois (evita vazamento de conexões). O FastAPI sabe usar isso automaticamente via um mecanismo chamado "dependency injection" 
def get_db():
    db = SessionLocal()
    try:
        yield db # Entrega a sessão pro endpoint usar
    finally:
        db.close() 

 