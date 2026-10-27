from fastapi import APIRouter

from .chat.router import router as chat_router
from .documents.router import router as documents_router
from .evaluation.router import router as evaluation_router
from .search.router import router as search_router


router = APIRouter()

router.include_router(chat_router, tags=["chat"])
router.include_router(search_router, tags=["search"])
router.include_router(documents_router, tags=["documents"])
router.include_router(evaluation_router, tags=["evaluation"])
