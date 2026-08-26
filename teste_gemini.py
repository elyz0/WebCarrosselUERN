from database import SessionLocal  # ajusta se o nome do módulo for outro
from resumir import resumir_pendentes

sessao = SessionLocal()
try:
    resultado = resumir_pendentes(sessao, limite=1)
    print(resultado)
finally:
    sessao.close()