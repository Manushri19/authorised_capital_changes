from decimal import Decimal
from datetime import date
from pydantic import BaseModel


class FieldValue(BaseModel):
    value: str | None
    confirmed: bool
    source_document: str | None
    source_field_machine: str | None
    source_field_human: str | None
    flag_code: str | None
    flag_message: str | None


class CapitalTableRow(BaseModel):
    row_number: int                     # 0 = On Incorporation, 1..N = events
    meeting_date: FieldValue
    authorised_from: FieldValue
    authorised_to: FieldValue
    meeting_type: FieldValue
    source_srn: str | None
    source_sh7_filename: str
    source_filing_date: date | None
    has_flags: bool
    flag_count: int
    flags: list[str]                    # list of flag_codes present in this row