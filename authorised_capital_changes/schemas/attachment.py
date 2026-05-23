from decimal import Decimal
from datetime import date
from pydantic import BaseModel


class BoardResolutionExtraction(BaseModel):
    source_filename: str
    cin: str | None
    meeting_date: date | None
    resolved_capital_amount: Decimal | None
    resolution_type: str | None
    source_field_machine: str = "Board Resolution operative clause"
    source_field_human: str = "Board resolution — resolved capital amount"
    extraction_confidence: float
    unconfirmed_fields: list[str]
    extraction_errors: list[str]


class EGMResolutionExtraction(BaseModel):
    source_filename: str
    cin: str | None
    meeting_date: date | None
    meeting_type: str | None
    # "EGM" or "AGM" — extracted from document body only.
    # Never inferred from filename.
    # A file named EGM_EventN whose body says "AGM" correctly
    # produces meeting_type = "AGM" with no flag.
    resolved_capital_amount: Decimal | None
    source_field_machine: str = "EGM/AGM Resolution operative clause"
    source_field_human: str = "EGM/AGM resolution — meeting type and resolved capital"
    extraction_confidence: float
    unconfirmed_fields: list[str]
    extraction_errors: list[str]


class MOAExtraction(BaseModel):
    source_filename: str
    cin: str | None
    incorporation_capital: Decimal | None
    equity_shares_count: int | None
    nominal_per_share: Decimal | None
    preference_shares_count: int | None
    preference_nominal_per_share: Decimal | None
    source_field_machine: str = "MOA Clause V"
    source_field_human: str = "Memorandum of Association — Clause V (Capital Clause)"
    extraction_confidence: float
    unconfirmed_fields: list[str]
    extraction_errors: list[str]