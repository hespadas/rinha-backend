from fastapi import APIRouter, HTTPException, Path
from datetime import datetime
from src.core import db
from src.schemas.transacao_schema import TransacaoIn

router = APIRouter()

@router.post("/{cliente_id}/transacoes")
async def create_transaction(cliente_id: int = Path(..., ge=1, le=5), transacao: TransacaoIn = ...):
    async with db.pool.acquire() as conn:
        async with conn.transaction():
            cliente = await conn.fetchrow("SELECT id, saldo, limite FROM clientes WHERE id = $1 FOR UPDATE", cliente_id)
            if not cliente:
                raise HTTPException(404, "Client not found")

            saldo = cliente["saldo"]
            limite = cliente["limite"]

            novo_saldo = saldo + transacao.valor if transacao.tipo == "c" else saldo - transacao.valor
            if transacao.tipo == "d" and novo_saldo < -limite:
                raise HTTPException(422, "Exceeds limit")

            await conn.execute("UPDATE clientes SET saldo = $1 WHERE id = $2", novo_saldo, cliente_id)
            await conn.execute("INSERT INTO transacoes (cliente_id, valor, tipo, descricao, realizada_em) VALUES ($1, $2, $3, $4, $5)",
                cliente_id, transacao.valor, transacao.tipo, transacao.descricao, datetime.utcnow())

            return {"limite": limite, "saldo": novo_saldo}
