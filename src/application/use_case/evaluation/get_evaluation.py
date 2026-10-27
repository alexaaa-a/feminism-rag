from src.application.interfaces.db.eval_db import EvaluationDBInterface
from src.domain.entities.evaluation import EvalReport


class GetEvaluationUseCase:
    def __init__(self, evaluation_db: EvaluationDBInterface) -> None:
        self._evaluation_db = evaluation_db

    async def __call__(self, run_id: str) -> EvalReport | None:
        return await self._evaluation_db.get_report(run_id)
