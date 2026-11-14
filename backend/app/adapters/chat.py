"""Compatibility endpoint for the retired free-form assistant.

The confirmed /api/plan workflow owns AI access. This endpoint never constructs
provider clients, spends a budget, executes a tool, or streams model prose.
"""

from dataclasses import dataclass

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.services import Services

CHAT_PATH = "/api/chat"
router = APIRouter()


@dataclass
class ChatBackend:
    services: Services


def create_chat_backend(services: Services) -> ChatBackend:
    return ChatBackend(services)


async def close_chat_backend(backend: ChatBackend) -> None:
    """Compatibility cleanup; the retired assistant owns no resources."""


@router.post(CHAT_PATH)
async def chat(request: Request) -> JSONResponse:
    # Read a bounded body so a disconnect is handled by the shared middleware.
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > 8192:
            break
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "ai_unavailable",
                "message": (
                    "Free-form AI chat is disabled. Use /api/plan and confirm its proposal "
                    "in the settings."
                ),
            }
        },
    )
