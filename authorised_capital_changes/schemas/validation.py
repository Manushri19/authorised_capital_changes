from decimal import Decimal
from datetime import date
from pydantic import BaseModel


class ArithmeticCheckResult(BaseModel):
    sh7_filename: str
    existing: Decimal
    difference: Decimal                 # from Field 6 Total addition line
    revised: Decimal
    computed_revised: Decimal           # existing + difference
    passed: bool
    discrepancy_amount: Decimal | None


class ContinuityCheckResult(BaseModel):
    event_index: int
    sh7_filename: str
    expected_from: Decimal
    actual_from: Decimal
    passed: bool
    source_of_expected: str             # previous SH-7 filename


class CrossDocumentCheckResult(BaseModel):
    event_index: int
    sh7_filename: str
    check_type: str                     # "DATE" or "CAPITAL_AMOUNT"
    sh7_value: str
    conflicting_document: str
    conflicting_value: str
    agreeing_documents: list[str]
    passed: bool
    flag_code: str


class DuplicateSH7CheckResult(BaseModel):
    meeting_date: date
    sh7_filenames: list[str]
    routed_to_human_review: bool


class ValidationReport(BaseModel):
    sh7_filename: str
    arithmetic_checks: list[ArithmeticCheckResult]
    continuity_checks: list[ContinuityCheckResult]
    cross_document_checks: list[CrossDocumentCheckResult]
    duplicate_checks: list[DuplicateSH7CheckResult]
    validation_passed: bool
    blocking_errors: list[str]
    non_blocking_flags: list[str]