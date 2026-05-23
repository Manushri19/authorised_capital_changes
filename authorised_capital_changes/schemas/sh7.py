from decimal import Decimal
from datetime import date
from pydantic import BaseModel, model_validator


class ShareBreakdown(BaseModel):
    equity_shares_count: int | None
    equity_nominal_per_share: Decimal | None
    equity_total_amount: Decimal | None
    preference_shares_count: int | None
    preference_nominal_per_share: Decimal | None
    preference_total_amount: Decimal | None
    unclassified_shares_count: int | None
    unclassified_total_amount: Decimal | None


class AuthorisedCapitalBlock(BaseModel):
    total_amount: Decimal
    breakdown: ShareBreakdown
    source_field_machine: str = "Section 9(a)"
    source_field_human: str = "Authorised capital after change, Section 9(a)"


class SH7Extraction(BaseModel):
    # Source — the filename of the SH-7 document this was extracted from
    source_filename: str | None = None

    # Identity — Fields 1 and 2
    cin: str
    company_name: str
    registered_address: str
    email: str

    # Event — Fields 3 and 4
    purpose: str
    meeting_date: date
    resolution_type: str                # "Ordinary" or "Special"

    # Capital change — Field 4(a)(i)
    existing_authorised_capital: Decimal
    revised_authorised_capital: Decimal
    difference_addition: Decimal | None = None

    # Post-change authorised capital — Section 9(a) ONLY
    # Sections 9(b), 9(c), 9(d) are NOT extracted
    authorised_capital: AuthorisedCapitalBlock

    # Filing identity — office use footer
    srn: str | None
    filing_date: date | None

    # Stamp duty — Field 11
    stamp_duty_state: str | None
    stamp_duty_amount: Decimal | None

    # Attachment filenames — Field 12, raw strings only, never interpreted
    attachment_filenames_raw: list[str]

    # Extraction quality
    extraction_confidence: float
    unconfirmed_fields: list[str]
    extraction_errors: list[str]

    @model_validator(mode='after')
    def check_section9a_vs_field4(self) -> 'SH7Extraction':
        if self.authorised_capital.total_amount != self.revised_authorised_capital:
            self.extraction_errors.append(
                f"Section 9(a) total {self.authorised_capital.total_amount} "
                f"does not match revised capital {self.revised_authorised_capital} "
                f"stated in Field 4(a)(i)"
            )
        return self