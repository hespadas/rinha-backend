from fastapi import FastAPI, HTTPException, Path
from src.rinha import db
from datetime import datetime, timezone

from src.rinha.model import TransacaoIn

app = FastAPI()
db.setup_db_events(app)

@app.get("/")
async def root():
    return {"status": "ok"}


@app.post("/clientes/{cliente_id}/transacoes")
async def transation_create(
    cliente_id: int = Path(..., ge=1, le=5),
    transacao: TransacaoIn = ...
):
    async with db.db_pool.acquire() as conn:
        async with conn.transaction():
            cliente = await conn.fetchrow(
                "SELECT id, saldo, limite FROM clientes WHERE id = $1 FOR UPDATE", cliente_id
            )
            if not cliente:
                raise HTTPException(status_code=404, detail="Client not found")

            saldo = cliente["saldo"]
            limite = cliente["limite"]

            novo_saldo = saldo + transacao.valor if transacao.tipo == "c" else saldo - transacao.valor

            if transacao.tipo == "d" and novo_saldo < -limite:
                raise HTTPException(status_code=422, detail="Exceeds limit")

            await conn.execute(
                """
                UPDATE clientes SET saldo = $1 WHERE id = $2
                """,
                novo_saldo, cliente_id
            )

            await conn.execute(
                """
                INSERT INTO transacoes (cliente_id, valor, tipo, descricao, realizada_em)
                VALUES ($1, $2, $3, $4, $5)
                """,
                cliente_id, transacao.valor, transacao.tipo, transacao.descricao, datetime.utcnow()
            )

            return {
                "limite": limite,
                "saldo": novo_saldo
            }


@app.get("/clientes/{cliente_id}/extrato")
async def obter_extrato(cliente_id: int = Path(..., ge=1, le=5)):
    async with db.db_pool.acquire() as conn:
        cliente = await conn.fetchrow(
            "SELECT saldo, limite FROM clientes WHERE id = $1", cliente_id
        )

        if not cliente:
            raise HTTPException(status_code=404, detail="Client not found")

        transacoes = await conn.fetch(
            """
            SELECT valor, tipo, descricao, realizada_em
            FROM transacoes
            WHERE cliente_id = $1
            ORDER BY realizada_em DESC
            LIMIT 10
            """,
            cliente_id
        )

        return {
            "saldo": {
                "total": cliente["saldo"],
                "limite": cliente["limite"],
                "data_extrato": datetime.now(timezone.utc).isoformat()
            },
            "ultimas_transacoes": [
                {
                    "valor": t["valor"],
                    "tipo": t["tipo"],
                    "descricao": t["descricao"],
                    "realizada_em": t["realizada_em"].isoformat()
                }
                for t in transacoes
            ]
        }