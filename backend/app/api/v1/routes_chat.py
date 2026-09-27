from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_session
from app.models.schemas import ChatRequest, ChatResponse
from app.services.rag.answer_generator import (
    NoContextError,
    RefusedError,
    generate_answer,
)
from app.services.retrieval.hybrid_search import hybrid_search

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def ask(
    body: ChatRequest,
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    chunks = await hybrid_search(session, body.question)
    try:
        return await generate_answer(body.question, chunks)
    except NoContextError:
        raise HTTPException(404, "nothing in the library matched that question")
    except RefusedError as exc:
        raise HTTPException(422, str(exc))
