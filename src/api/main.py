from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from src.api.routes import transacoes, extratos
from src.core import db

app = FastAPI(default_response_class=ORJSONResponse)
db.setup_db_events(app)

app.include_router(transacoes.router, prefix="/clientes")
app.include_router(extratos.router, prefix="/clientes")

@app.get("/")
async def health_check():
    return {"status": "ok"}
