from fastapi import FastAPI, HTTPException, Path
from src import db
from datetime import datetime
from fastapi.responses import ORJSONResponse, Response

from src.model import TransacaoIn

app = FastAPI(default_response_class=ORJSONResponse)
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
async def get_extrato(cliente_id: int = Path(..., ge=1)):
    async with db.db_pool.acquire() as conn:
        sql = """
        WITH cliente AS (
          SELECT saldo, limite
          FROM clientes
          WHERE id = $1
        )
        SELECT (
          json_build_object(
            'saldo', json_build_object(
              'total', c.saldo,
              'limite', c.limite,
              'data_extrato',
                to_char(now() AT TIME ZONE 'UTC',
                        'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"')
            ),
            'ultimas_transacoes', coalesce(sub.arr, '[]')
          )
        )::text
        FROM cliente c
        CROSS JOIN LATERAL (
          SELECT json_agg(
                   json_build_object(
                     'valor', t.valor,
                     'tipo',  t.tipo,
                     'descricao', t.descricao,
                     'realizada_em',
                       to_char(t.realizada_em AT TIME ZONE 'UTC',
                               'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"')
                   )
                   ORDER BY t.realizada_em DESC, t.id DESC
                 ) AS arr
          FROM (
            SELECT id, valor, tipo, descricao, realizada_em
            FROM transacoes
            WHERE cliente_id = $1
            ORDER BY realizada_em DESC, id DESC
            LIMIT 10
          ) t
        ) AS sub;
        """
        row = await conn.fetchval(sql, cliente_id)
        if not row:
            raise HTTPException(status_code=404, detail="Client not found")
        return Response(content=row, media_type="application/json")