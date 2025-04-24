import asyncpg, asyncio
from fastapi import FastAPI

db_pool: asyncpg.Pool | None = None

DATABASE_CONFIG = {
    "user": "espadas",
    "password": "espadas123",
    "database": "rinha",
    "host": "db",
    "port": 5432,
    "min_size": 5,
    "max_size": 20,
}

async def init_db_pool():
    global db_pool
    retries = 30
    for i in range(1, retries + 1):
        try:
            db_pool = await asyncpg.create_pool(**DATABASE_CONFIG)
            return
        except Exception as e:
            print(f"⏳ Try {i}/{retries} - Error: {e}")
            await asyncio.sleep(2)
    raise RuntimeError("Failed to connect to the database after multiple attempts.")

async def close_db_pool():
    if db_pool:
        await db_pool.close()


def setup_db_events(app: FastAPI):
    print("Setting up database events...")

    @app.on_event("startup")
    async def on_startup():
        print("Startup event triggered - initializing DB pool...")
        await init_db_pool()

    @app.on_event("shutdown")
    async def on_shutdown():
        print("Shutdown event triggered - closing DB pool...")
        await close_db_pool()
