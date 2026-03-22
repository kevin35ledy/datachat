from __future__ import annotations
from fastapi import APIRouter
from app.api.v1 import health, connections, chat, schema as schema_router

api_router = APIRouter()
api_router.include_router(health.router, prefix="/v1", tags=["health"])
api_router.include_router(connections.router, prefix="/v1/connections", tags=["connections"])
api_router.include_router(chat.router, prefix="/v1/chat", tags=["chat"])
api_router.include_router(schema_router.router, prefix="/v1/schema", tags=["schema"])
