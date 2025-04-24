from fastapi import FastAPI
from src.rinha import db

app = FastAPI()
db.setup_db_events(app)

@app.get("/")
async def root():
    return {"status": "ok"}


@app.get("/test-db")
async def test_db():
    try:
        async with db.db_pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            return {"db": result}
    except Exception as e:
        return {"error": f"Database error: {str(e)}"}

