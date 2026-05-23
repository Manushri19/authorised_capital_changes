from pydantic import BaseModel


class FlagEntry(BaseModel):
    flag_code: str
    row_number: int
    field_name: str
    flag_message: str
    source_document: str
    conflicting_document: str | None


class DiscrepancyReport(BaseModel):
    run_id: str
    generated_at: str
    total_documents_processed: int
    sh7_documents_found: int
    sh7_documents_extracted: int
    sh7_documents_assembled: int
    sh7_documents_blocked: int
    flags: list[FlagEntry]
    arithmetic_failures: list[dict]
    continuity_failures: list[dict]
    cross_document_conflicts: list[dict]
    duplicate_sh7s: list[dict]
    unmatched_attachments: dict[str, list[str]]
    blocked_sh7s: list[dict]
    corroborations: list[dict]
    # corroboration entry shape:
    # { check, result ("AGREED"|"DISAGREED"), moa_figure,
    #   sh7_figure, source_moa, source_sh7, note (only if DISAGREED) }