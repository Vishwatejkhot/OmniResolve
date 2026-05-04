import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from api.routes import cases, channels, webhooks
from api.websocket import router as ws_router
from graphrag.neo4j_client import apply_schema, close as close_neo4j

@asynccontextmanager
async def lifespan(app: FastAPI):
    await apply_schema()
    yield
    await close_neo4j()

app = FastAPI(
    title="OmniResolve API",
    description="Unified Omnichannel E-Commerce Dispute Intelligence System",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cases.router, prefix="/api/v1/cases", tags=["cases"])
app.include_router(channels.router, prefix="/api/v1/channels", tags=["channels"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
app.include_router(ws_router, tags=["websocket"])

@app.get("/health")
async def health():
    return {"status": "ok", "service": "omni-resolve"}

@app.get("/")
async def root():
    return {"message": "OmniResolve API — see /docs"}
