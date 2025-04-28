from fastapi import APIRouter, HTTPException, Path, FastAPI
from fastapi.responses import ORJSONResponse, Response

from src.core import db

app = FastAPI(default_response_class=ORJSONResponse)
router = APIRouter()

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