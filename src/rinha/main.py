from fastapi import FastAPI
from .db import setup_db_events, db_pool, init_db_pool

app = FastAPI()
setup_db_events(app)

@app.get("/")
async def root():
    return {"status": "ok"}


@app.get("/test-db")
async def test_db():
    from .db import db_pool
    if db_pool is None:
        return {"error": "DB pool is not initialized."}
    try:
        async with db_pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            return {"db": result}
    except Exception as e:
        return {"error": f"Database error: {str(e)}"}

