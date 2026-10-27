from dataclasses import asdict, fields
from typing import Any

from src.domain.entities.chat import (
    AnswerDiagnostics,
    ChatMessage,
    ChatSession,
    Citation,
    MessageRole,
)
from src.domain.entities.chunk import ParentChunk
from src.domain.entities.evaluation import EvalCaseResult, EvalReport
from src.domain.entities.ingest import DocumentRecord, DocumentStatus, IngestRun, IngestStatus


def _known_fields(cls: type, data: dict) -> dict[str, Any]:
    allowed = {item.name for item in fields(cls)}
    return {key: value for key, value in data.items() if key in allowed}


def _without_id(document: dict) -> dict:
    data = dict(document)
    data.pop("_id", None)
    return data


def document_record_to_document(record: DocumentRecord) -> dict:
    data = asdict(record)
    data["status"] = str(record.status)
    data["_id"] = record.document_id
    return data


def document_record_from_document(document: dict) -> DocumentRecord:
    data = _known_fields(DocumentRecord, _without_id(document))
    data["status"] = DocumentStatus(data.get("status") or DocumentStatus.INDEXED)
    return DocumentRecord(**data)


def parent_to_document(parent: ParentChunk) -> dict:
    data = asdict(parent)
    data["_id"] = parent.parent_id
    return data


def parent_from_document(document: dict) -> ParentChunk:
    return ParentChunk(**_known_fields(ParentChunk, _without_id(document)))


def session_to_document(session: ChatSession) -> dict:
    data = asdict(session)
    data["_id"] = session.session_id
    return data


def session_from_document(document: dict) -> ChatSession:
    return ChatSession(**_known_fields(ChatSession, _without_id(document)))


def message_to_document(message: ChatMessage) -> dict:
    data = asdict(message)
    data["role"] = str(message.role)
    data["_id"] = message.message_id
    return data


def message_from_document(document: dict) -> ChatMessage:
    data = _known_fields(ChatMessage, _without_id(document))
    data["role"] = MessageRole(data.get("role") or MessageRole.USER)
    data["citations"] = [
        Citation(**_known_fields(Citation, item))
        for item in (data.get("citations") or [])
        if isinstance(item, dict)
    ]
    diagnostics = data.get("diagnostics")
    data["diagnostics"] = (
        AnswerDiagnostics(**_known_fields(AnswerDiagnostics, diagnostics))
        if isinstance(diagnostics, dict)
        else None
    )
    return ChatMessage(**data)


def ingest_run_to_document(run: IngestRun) -> dict:
    data = asdict(run)
    data["status"] = str(run.status)
    data["_id"] = run.run_id
    return data


def ingest_run_from_document(document: dict) -> IngestRun:
    data = _known_fields(IngestRun, _without_id(document))
    data["status"] = IngestStatus(data.get("status") or IngestStatus.RUNNING)
    return IngestRun(**data)


def eval_report_to_document(report: EvalReport) -> dict:
    data = asdict(report)
    data["hit_at"] = {str(key): value for key, value in report.hit_at.items()}
    data["evidence_hit_at"] = {str(key): value for key, value in report.evidence_hit_at.items()}
    data["_id"] = report.run_id
    return data


def eval_report_from_document(document: dict) -> EvalReport:
    data = _known_fields(EvalReport, _without_id(document))
    data["hit_at"] = {int(key): value for key, value in (data.get("hit_at") or {}).items()}
    data["evidence_hit_at"] = {
        int(key): value for key, value in (data.get("evidence_hit_at") or {}).items()
    }
    data["results"] = [
        EvalCaseResult(**_known_fields(EvalCaseResult, item))
        for item in (data.get("results") or [])
        if isinstance(item, dict)
    ]
    return EvalReport(**data)
