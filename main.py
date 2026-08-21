from fastapi import FastAPI, Depends, HTTPException 
from sqlalchemy.orm import Session
from database import Base, engine, get_db
from fastapi.middleware.cors import CORSMiddleware
import models 
import schemas 
import scraper  
import resumir 


Base.metadata.create_all(bind=engine) #essa linha é o que efetivamente cria a tabela no banco, se ela ainda não existir.

app = FastAPI()
# Libera o front-end (rodando em outra origem) para acessar a API.
# Em producao, trocar allow_origins=["*"] pela URL real da TV/painel.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
) 

@app.get("/")
def home():
    return {"status": "Backend do carrossel UERN funcionando!"} 


 
# Cadastrar um conteúdo manualmente
@app.post("/conteudos", response_model=schemas.ConteudoResponse) # Diz ao FastAPI qual schema usar 
#No POST cria-se um objeto Conteudo (que vem do models.py) a partir dos dados validados (conteudo, que já é um ConteudoCreate, vindo do schemas.py). 
def criar_conteudo(conteudo: schemas.ConteudoCreate, db: Session = Depends(get_db)): # "Dependes" é o "dependency injection" — o FastAPI chama get_db() automaticamente antes do endpoint rodar

    novo = models.Conteudo(
        tipo=conteudo.tipo,
        titulo=conteudo.titulo,
        texto_original=conteudo.texto_original,
        imagem_url=conteudo.imagem_url,
        url_origem=conteudo.url_origem,
        data_expiracao=conteudo.data_expiracao,
        origem="manual",
        status="ativo",
    ) 

    # Usamos db.add + db.commit pra salvar. 
    db.add(novo)
    db.commit()
    db.refresh(novo) # O db.refresh(novo) atualiza o objeto Python com o id que o banco acabou de gerar.
    return novo

 
# Listar conteúdos (com filtro opcional por tipo)
@app.get("/conteudos", response_model=list[schemas.ConteudoResponse])  
#No GET filtramos por status "ativo" sempre (não queremos mostrar conteúdo expirado/oculto), e opcionalmente por tipo (pra separar notícia de edital).
def listar_conteudos(tipo: str | None = None, status: str | None = "ativo", db: Session = Depends(get_db)): 

    query = db.query(models.Conteudo) 

    if status:
        query = query.filter(models.Conteudo.status == status)
    if tipo:
        query = query.filter(models.Conteudo.tipo == tipo) 

    return query.all()  

 
# Editar um conteúdo existente
@app.put("/conteudos/{conteudo_id}", response_model=schemas.ConteudoResponse) #{conteudo_id} na URL: é um "path parameter". Ele captura o número da URL e entrega como argumento pra função.
#No PUT
def atualizar_conteudo(conteudo_id: int, dados: schemas.ConteudoUpdate, db: Session = Depends(get_db)): 

    conteudo = db.query(models.Conteudo).filter(models.Conteudo.id == conteudo_id).first() 

    if not conteudo:
        raise HTTPException(status_code=404, detail="Conteudo nao encontrado") # Se o id não existir no banco, devolve um erro 404 (não encontrado) em vez de quebrar ou devolver algo estranho.

    dados_atualizados = dados.model_dump(exclude_unset=True) # Pega só os campos que a pessoa de fato enviou na edição (ignora os que ficaram como None por padrão). Dessa forma editar só o "status", por exemplo, não apaga os outros campos sem querer.

    for campo, valor in dados_atualizados.items():
        setattr(conteudo, campo, valor) # Aplica cada mudança recebida no objeto do banco, campo por campo.

    db.commit()
    db.refresh(conteudo) #  

    return conteudo

 
# "Apagar" um conteúdo (oculta, nao remove do banco)
@app.delete("/conteudos/{conteudo_id}") 
#No DELETE 
def ocultar_conteudo(conteudo_id: int, db: Session = Depends(get_db)): 

    conteudo = db.query(models.Conteudo).filter(models.Conteudo.id == conteudo_id).first() 

    if not conteudo:
        raise HTTPException(status_code=404, detail="Conteudo nao encontrado")

    conteudo.status = "oculto"
    db.commit() 

    return {"status": "Conteudo ocultado com sucesso", "id": conteudo_id}  


# Consultar o modo atual da TV
@app.get("/config", response_model=schemas.ConfigTVResponse)
def obter_config(db: Session = Depends(get_db)): 

    config = db.query(models.ConfigTV).first() 

    if not config:
        # Se ainda nao existe nenhuma config, cria uma com valor padrao "geral"
        config = models.ConfigTV(modo_atual="geral")
        db.add(config)
        db.commit()
        db.refresh(config) 

    return config

 
# Trocar o modo da TV (geral ou edital)
@app.put("/config", response_model=schemas.ConfigTVResponse)
def atualizar_config(dados: schemas.ConfigTVUpdate, db: Session = Depends(get_db)): 

    if dados.modo_atual not in ["geral", "edital"]:
        raise HTTPException(status_code=400, detail="modo_atual deve ser 'geral' ou 'edital'")

    config = db.query(models.ConfigTV).first() 

    if not config:
        config = models.ConfigTV(modo_atual=dados.modo_atual)
        db.add(config)
    else:
        config.modo_atual = dados.modo_atual

    db.commit()
    db.refresh(config) 

    return config


# Importa notícias/editais do RSS do portal (sem duplicar url_origem).
@app.post("/scraper/sincronizar", response_model=schemas.ScraperSincronizarResponse)
def sincronizar_portal(db: Session = Depends(get_db)):
    return scraper.sincronizar(db) 


# Gera o resumo (via IA) dos conteúdos que ainda não têm resumo
@app.post("/scraper/resumir")
def resumir_portal(db: Session = Depends(get_db)):
    return resumir.resumir_pendentes(db)

