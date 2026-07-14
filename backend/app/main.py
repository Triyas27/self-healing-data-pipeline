from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, quarantine, runs, stats
from app.db.session import SessionLocal, init_db
from app.models import CustomerReference
from app.synthetic.generator import known_customer_ids


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        if db.query(CustomerReference).count() == 0:
            for cid in known_customer_ids():
                db.add(CustomerReference(customer_id=cid))
            db.commit()
    finally:
        db.close()
    yield


app = FastAPI(title="Self-Healing Data Pipeline", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(runs.router)
app.include_router(quarantine.router)
app.include_router(stats.router)
