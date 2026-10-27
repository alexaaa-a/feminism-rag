from src.application.interfaces.db.eval_db import EvaluationDBInterface
from src.domain.entities.evaluation import EvalReport


class ListEvaluationsUseCase:
    def __init__(self, evaluation_db: EvaluationDBInterface) -> None:
        self._evaluation_db = evaluation_db

    async def __call__(self, limit: int = 20) -> list[EvalReport]:
        return await self._evaluation_db.list_reports(limit=limit)
