import json
from dataclasses import asdict

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException, Request, status
from starlette.responses import StreamingResponse

from src.application.dto.chat import AskRequest
from src.application.use_case.chat.ask_question import AskQuestionUseCase
from src.application.use_case.chat.create_session import CreateSessionUseCase
from src.application.use_case.chat.delete_session import DeleteSessionUseCase
from src.application.use_case.chat.get_session import GetSessionUseCase
from src.application.use_case.chat.list_sessions import ListSessionsUseCase
from src.application.use_case.chat.stream_answer import StreamAnswerUseCase
from src.domain.entities.chat import ChatMessage, ChatSession
from src.presentation.api.deps import client_id_from
from src.presentation.api.v1.chat.schema import (
    AskIn,
    CreateSessionIn,
    MessageOut,
    SessionDetailOut,
    SessionOut,
    SessionsOut,
)
from src.presentation.api.v1.common import CitationOut, DiagnosticsOut, answer_to_response

router = APIRouter(route_class=DishkaRoute)

_ERROR_STATUS = {
    "empty_question": status.HTTP_400_BAD_REQUEST,
    "question_too_long": status.HTTP_400_BAD_REQUEST,
    "session_not_found": status.HTTP_404_NOT_FOUND,
    "save_failed": status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def _session_to_response(session: ChatSession) -> SessionOut:
    return SessionOut(
        session_id=session.session_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages_count=session.messages_count,
    )


def _message_to_response(message: ChatMessage) -> MessageOut:
    return MessageOut(
        message_id=message.message_id,
        role=str(message.role),
        content=message.content,
        created_at=message.created_at,
        refused=message.refused,
        citations=[CitationOut(**asdict(citation)) for citation in message.citations],
        diagnostics=(
            DiagnosticsOut(**asdict(message.diagnostics))
            if message.diagnostics is not None
            else None
        ),
    )


@router.post(
    "/chat/ask",
    status_code=status.HTTP_200_OK,
    description="Задать вопрос ассистенту. session_id задан - отвечаем с учётом истории",
)
async def ask(
        body: AskIn,
        uc: FromDishka[AskQuestionUseCase],
        request: Request,
):
    result = await uc(
        AskRequest(
            question=body.question,
            session_id=body.session_id,
            client_id=client_id_from(request),
            top_k=body.top_k,
            filters=body.filters.to_entity(),
            use_history=body.use_history,
        )
    )

    if result.error or result.answer is None:
        raise HTTPException(
            status_code=_ERROR_STATUS.get(
                result.error or "",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
            detail=result.message or "Не удалось ответить на вопрос",
        )

    return answer_to_response(result.answer)


@router.post(
    "/chat/stream",
    description="Тот же ответ, но потоком Server-Sent Events: meta, delta, done",
)
async def stream(
        body: AskIn,
        uc: FromDishka[StreamAnswerUseCase],
        request: Request,
):
    ask_request = AskRequest(
        question=body.question,
        session_id=body.session_id,
        client_id=client_id_from(request),
        top_k=body.top_k,
        filters=body.filters.to_entity(),
        use_history=body.use_history,
    )

    async def event_stream():
        async for event in uc(ask_request):
            payload: dict = {}
            if event.text:
                payload["text"] = event.text
            if event.answer is not None:
                payload["answer"] = answer_to_response(event.answer).model_dump(mode="json")
            if event.error:
                payload["error"] = event.error
                payload["message"] = event.message
            yield (
                f"event: {event.event}\n"
                f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post(
    "/chat/sessions",
    status_code=status.HTTP_201_CREATED,
    response_model=SessionOut,
    description="Создать диалог",
)
async def create_session(
        body: CreateSessionIn,
        uc: FromDishka[CreateSessionUseCase],
        request: Request,
):
    result = await uc(title=body.title, client_id=client_id_from(request))
    if result.session is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось создать диалог",
        )
    return _session_to_response(result.session)


@router.get(
    "/chat/sessions",
    status_code=status.HTTP_200_OK,
    response_model=SessionsOut,
    description="Список диалогов",
)
async def list_sessions(
        uc: FromDishka[ListSessionsUseCase],
        request: Request,
        limit: int = 50,
        offset: int = 0,
):
    sessions = await uc(
        client_id=client_id_from(request),
        limit=limit,
        offset=offset,
    )
    return SessionsOut(sessions=[_session_to_response(item) for item in sessions])


@router.get(
    "/chat/sessions/{session_id}",
    status_code=status.HTTP_200_OK,
    response_model=SessionDetailOut,
    description="Диалог вместе с историей сообщений",
)
async def get_session(
        session_id: str,
        uc: FromDishka[GetSessionUseCase],
):
    found = await uc(session_id)
    if found is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Диалог не найден",
        )
    return SessionDetailOut(
        session=_session_to_response(found.session),
        messages=[_message_to_response(message) for message in found.messages],
    )


@router.delete(
    "/chat/sessions/{session_id}",
    status_code=status.HTTP_200_OK,
    description="Удалить диалог вместе с сообщениями",
)
async def delete_session(
        session_id: str,
        uc: FromDishka[DeleteSessionUseCase],
):
    if not await uc(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Диалог не найден",
        )
    return {"status": "deleted"}
