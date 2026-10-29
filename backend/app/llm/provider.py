from typing import Protocol

from app.schemas import Assessment, LoadedModel, SuppliedSource


class ModelProvider(Protocol):
    async def installed_model(self) -> dict: ...
    async def loaded_model(self) -> LoadedModel: ...
    async def generate(self, messages: list[dict], schema: dict) -> dict: ...


def validate_citations(assessment: Assessment, sources: list[SuppliedSource]) -> None:
    from app.core.errors import BackendError
    allowed = {source.id for source in sources}
    if len(set(assessment.source_ids)) != len(assessment.source_ids) or not set(assessment.source_ids) <= allowed:
        raise BackendError("invalid_model_output", "The model returned invalid or duplicate source references.")
    if sources and not assessment.insufficient_evidence and not assessment.source_ids:
        raise BackendError("invalid_model_output", "A source-grounded answer must cite a supplied source or abstain.")
