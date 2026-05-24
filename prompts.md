# Primary Skill Used for Research and Development:
/interview-me : Ask me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask the questions one at a time.

If a question can be answered by exploring the codebase, explore the codebase instead.



# AUTHORISED CAPITAL CHANGES SYSTEM
# Complete Build Specification 
### This is a curated collection of initial prompts I created for this project which were later customised based further specialised needs or errors/bugs encountered during the development process.
 
---

## PART 1 — GROUND TRUTH DECISIONS

1. Output table: Authorised capital only — four columns exactly as in the image 
2. AGM/EGM: Confirmed from EGM resolution document body when available — flag removed when confirmed. Flag raised only when attachment unavailable or did not state type explicitly
3. On Incorporation source: first SH-7's `existing_authorised_capital` field — not MOA
4. Pre-change breakdown Row 0: Option A — arithmetic derivation (existing ÷ nominal). Multi-class guard applies. Called only for Row 0 — never for Rows 1–N
5. MOA extraction: kept but scope reduced to optional corroboration only. Never sources or blocks any row. Result goes to discrepancy report corroborations only
6. MOA independent search: removed from Node 3. MOA linked only if explicitly listed in Field 12
7. Duplicate SH-7 same meeting date: both routed to human review
8. Arithmetic validation: separate explicit Node 6
9. Dataset: SH7.md provided is the actual Event 1 document — all figures consistent with it
10. Traceability: both machine field reference and human-readable label on every FieldValue
11. Flags in output: inline ⚠️ symbol in cell + numbered footnote below table
12. Date display format: "DD Month YYYY" (e.g. "22 March 2018") — rendered in Node 8, not stored in FieldValue
14. compute_prechange_breakdown invoked only for Row 0. Rows 1–N copy From from previous row's To string directly
15. Capital progression covers all four cases: incorporation to equity only, equity to equity, equity to equity+preference, equity+preference to equity+preference

---

## PART 2 — DUMMY DATASET SPECIFICATION

### 2.1 Company Identity

```
CIN:                U85123DL2018PTC312456
Company Name:       NEXUS BRIGHTLEARN SOLUTIONS PRIVATE LIMITED
Registered Address: KRISHNA TOWER PLOT NO-45 SECTOR-12 DWARKA NEW DELHI
                    New Delhi Delhi 110075
Email:              arunsethi@outlook.com
Director:           ARUN VIKRAM SETHI
DIN:                08745632
```

### 2.2 Capital Event Ground Truth

```
Event 1 — SH7_Event1_2018.md  (THIS IS THE ACTUAL SH7.md PROVIDED — USE AS-IS)
    Meeting Date:     22/03/2018
    Existing Capital: ₹1,50,000
    Revised Capital:  ₹3,00,000
    Difference:       ₹1,50,000
    Post-change Section 9(a):
        Equity shares:    30,000 of ₹10 each = ₹3,00,000
        Preference:       0
        Total:            ₹3,00,000 ✓
    Resolution:       Ordinary
    SRN:              H34567891
    Filing Date:      22/03/2018
    Stamp Duty:       ₹1,500 (Delhi)
    Attachments in Field 12: CTC_EGM.pdf, MOA New.pdf,
                             Notice of EGM.pdf, CTC_Board Meeting.pdf
    Inconsistency:    None — clean

Event 2 — SH7_Event2_2019.md
    Meeting Date:     15/05/2019
    Existing Capital: ₹3,00,000
    Revised Capital:  ₹50,00,000
    Difference:       ₹47,00,000
    Post-change Section 9(a):
        Equity shares:    5,00,000 of ₹10 each = ₹50,00,000
        Preference:       0
        Total:            ₹50,00,000 ✓
    Resolution:       Ordinary
    SRN:              H45678902
    Filing Date:      15/05/2019
    Stamp Duty:       ₹4,700 (Delhi)
    Attachments in Field 12: CTC_EGM_2019.pdf, MOA_2019.pdf,
                             CTC_Board Meeting_2019.pdf
    Inconsistency:    None — clean

Event 3 — SH7_Event3_2021.md
    Meeting Date:     10/09/2021        ← SH-7 states this date
    Existing Capital: ₹50,00,000
    Revised Capital:  ₹2,00,00,000
    Difference:       ₹1,50,00,000
    Post-change Section 9(a):
        Equity shares:    18,00,000 of ₹10 each = ₹1,80,00,000
        Preference:        2,00,000 of ₹10 each = ₹20,00,000
        Total:            ₹2,00,00,000 ✓
    Resolution:       Ordinary
    SRN:              H56789013
    Filing Date:      10/09/2021
    Stamp Duty:       ₹15,000 (Delhi)
    Attachments in Field 12: CTC_EGM_2021.pdf, MOA_2021.pdf,
                             CTC_Board Meeting_2021.pdf
    Inconsistency:    DATE MISMATCH
        EGM_Event3_2021.md states:          25/08/2021
        BoardMeeting_Event3_2021.md states: 25/08/2021
        SH-7 states:                        10/09/2021
        Expected flag: non-blocking ⚠️ [1] on meeting_date cell

Event 4 — SH7_Event4_2024.md
    Meeting Date:     28/03/2024
    Existing Capital: ₹2,00,00,000
    Revised Capital:  ₹10,00,00,000
    Difference:       ₹8,00,00,000
    Post-change Section 9(a):
        Equity shares:    99,00,000 of ₹10 each = ₹9,90,00,000
        Preference:        1,00,000 of ₹10 each = ₹10,00,000
        Total:            ₹10,00,00,000 ✓
    Resolution:       Special
    SRN:              H67890124
    Filing Date:      28/03/2024
    Stamp Duty:       ₹80,000 (Delhi)
    Attachments in Field 12: CTC_EGM_2024.pdf, MOA_2024.pdf,
                             CTC_Board Meeting_2024.pdf
    Inconsistency:    CAPITAL FIGURE MISMATCH
        SH-7 states revised capital:        ₹10,00,00,000
        BoardMeeting_Event4_2024.md states: ₹8,00,00,000
        EGM_Event4_2024.md states:          ₹10,00,00,000
        Expected flag: non-blocking ⚠️ [2] on authorised_to cell
```

### 2.3 Attachment Document Specifications

**ExampleBoard Meeting Resolutions**

```
BoardMeeting_Event1_2018.md
    Meeting date:      22/03/2018
    Resolved capital:  ₹3,00,000
    Resolution type:   Ordinary
    Status:            CERTIFIED_COPY (contains "CERTIFIED TRUE COPY" header)

BoardMeeting_Event2_2019.md
    Meeting date:      15/05/2019
    Resolved capital:  ₹50,00,000
    Resolution type:   Ordinary
    Status:            CERTIFIED_COPY

BoardMeeting_Event3_2021.md    ← planted inconsistency
    Meeting date:      25/08/2021  (differs from SH-7's 10/09/2021)
    Resolved capital:  ₹2,00,00,000
    Resolution type:   Ordinary
    Status:            CERTIFIED_COPY

BoardMeeting_Event4_2024.md    ← planted inconsistency
    Meeting date:      28/03/2024
    Resolved capital:  ₹8,00,00,000  (differs from SH-7's ₹10,00,00,000)
    Resolution type:   Special
    Status:            CERTIFIED_COPY
```

**Example EGM/AGM Resolution Documents**

```
EGM_Event1_2018.md
    Meeting date:      22/03/2018
    Meeting type:      EGM  (word "EGM" appears literally in document body)
    Resolved capital:  ₹3,00,000
    Status:            CERTIFIED_COPY

EGM_Event2_2019.md
    Meeting date:      15/05/2019
    Meeting type:      EGM  (word "EGM" appears literally in document body)
    Resolved capital:  ₹50,00,000
    Status:            CERTIFIED_COPY

EGM_Event3_2021.md             ← planted inconsistency on date
    Meeting date:      25/08/2021  (differs from SH-7's 10/09/2021)
    Meeting type:      AGM  (word "AGM" appears literally in document body)
    Resolved capital:  ₹2,00,00,000
    Status:            CERTIFIED_COPY
    Note: file is named EGM_Event3 but body says AGM — this is valid,
          produces no flag. Classifier assigns EGM_RESOLUTION from filename.
          Node 4 extracts meeting_type "AGM" from body. These are independent.

EGM_Event4_2024.md
    Meeting date:      28/03/2024
    Meeting type:      AGM  (word "AGM" appears literally in document body)
    Resolved capital:  ₹10,00,00,000  (agrees with SH-7)
    Status:            CERTIFIED_COPY
```

**Example MOA Documents**

```
MOA_Event1_2018.md
    Clause V capital:  ₹1,50,000
    Equity shares:     15,000 of ₹10 each
    Preference shares: 0
    Status:            DRAFT

MOA_Event2_2019.md
    Clause V capital:  ₹50,00,000
    Equity shares:     5,00,000 of ₹10 each
    Preference shares: 0
    Status:            DRAFT

MOA_Event3_2021.md
    Clause V capital:  ₹2,00,00,000
    Equity shares:     18,00,000 of ₹10 each
    Preference shares:  2,00,000 of ₹10 each
    Status:            DRAFT

MOA_Event4_2024.md
    Clause V capital:  ₹10,00,00,000
    Equity shares:     99,00,000 of ₹10 each
    Preference shares:  1,00,000 of ₹10 each
    Status:            DRAFT
```

### 2.4 Example Capital Chain Verification

```
On incorporation:    ₹1,50,000    = 15,000 eq × ₹10        (Row 0 — derived)
↓
Event 1 From:        ₹1,50,000    = 15,000 eq × ₹10        (copied from Row 0 To)
Event 1 To:          ₹3,00,000    = 30,000 eq × ₹10
↓
Event 2 From:        ₹3,00,000    = 30,000 eq × ₹10        (copied from E1 To)
Event 2 To:          ₹50,00,000   = 5,00,000 eq × ₹10
↓
Event 3 From:        ₹50,00,000   = 5,00,000 eq × ₹10      (copied from E2 To)
Event 3 To:          ₹2,00,00,000 = 18,00,000 eq × ₹10
                                  +  2,00,000 pref × ₹10
                     1,80,00,000 + 20,00,000 = 2,00,00,000 ✓
↓
Event 4 From:        ₹2,00,00,000 = 18,00,000 eq × ₹10
                                  +  2,00,000 pref × ₹10   (copied from E3 To)
Event 4 To:          ₹10,00,00,000 = 99,00,000 eq × ₹10
                                   +  1,00,000 pref × ₹10
                     9,90,00,000 + 10,00,000 = 10,00,00,000 ✓

Continuity checks (Node 6 will verify):
    E1 existing ₹1,50,000     == E0 revised ₹1,50,000     ✓
    E2 existing ₹3,00,000     == E1 revised ₹3,00,000     ✓
    E3 existing ₹50,00,000    == E2 revised ₹50,00,000    ✓
    E4 existing ₹2,00,00,000  == E3 revised ₹2,00,00,000  ✓

Arithmetic checks (Node 6 will verify):
    E1: ₹1,50,000 + ₹1,50,000       = ₹3,00,000       ✓
    E2: ₹3,00,000 + ₹47,00,000      = ₹50,00,000      ✓
    E3: ₹50,00,000 + ₹1,50,00,000   = ₹2,00,00,000    ✓
    E4: ₹2,00,00,000 + ₹8,00,00,000 = ₹10,00,00,000   ✓
```

### 2.5 Example Output Table — Definitive

```
AUTHORISED SHARE CAPITAL CHANGES
Company: NEXUS BRIGHTLEARN SOLUTIONS PRIVATE LIMITED
CIN: U85123DL2018PTC312456

┌──────────────────────┬────────────────────────────────────────────┬────────────────────────────────────────────────────────┬──────────┐
│ Date of              │         Particulars of Change              │                                                        │ AGM/EGM  │
│ Shareholder's        ├────────────────────────────────────────────┼────────────────────────────────────────────────────────┤          │
│ Meeting              │ From                                       │ To                                                     │          │
├──────────────────────┼────────────────────────────────────────────┼────────────────────────────────────────────────────────┼──────────┤
│ On incorporation     │ -                                          │ ₹1,50,000 divided into 15,000 Equity Shares of         │ -        │
│                      │                                            │ ₹10 each                                               │          │
├──────────────────────┼────────────────────────────────────────────┼────────────────────────────────────────────────────────┼──────────┤
│ 22 March 2018        │ ₹1,50,000 divided into 15,000 Equity       │ ₹3,00,000 divided into 30,000 Equity Shares of         │ EGM      │
│                      │ Shares of ₹10 each                         │ ₹10 each                                               │          │
├──────────────────────┼────────────────────────────────────────────┼────────────────────────────────────────────────────────┼──────────┤
│ 15 May 2019          │ ₹3,00,000 divided into 30,000 Equity       │ ₹50,00,000 divided into 5,00,000 Equity Shares of      │ EGM      │
│                      │ Shares of ₹10 each                         │ ₹10 each                                               │          │
├──────────────────────┼────────────────────────────────────────────┼────────────────────────────────────────────────────────┼──────────┤
│ 10 September 2021    │ ₹50,00,000 divided into 5,00,000 Equity    │ ₹2,00,00,000 divided into 18,00,000 Equity Shares of   │ AGM      │
│              │ Shares of ₹10 each                         │ ₹10 each and 2,00,000 Preference Shares of ₹10 each    │          │
├──────────────────────┼────────────────────────────────────────────┼────────────────────────────────────────────────────────┼──────────┤
│ 28 March 2024        │ ₹2,00,00,000 divided into 18,00,000        │ ₹10,00,00,000 divided into 99,00,000 Equity Shares     │ AGM      │
│                      │ Equity Shares of ₹10 each and 2,00,000     │ of ₹10 each and 1,00,000 Preference Shares of          │          │
│                      │ Preference Shares of ₹10 each              │ ₹10 each                                           │          │
└──────────────────────┴────────────────────────────────────────────┴────────────────────────────────────────────────────────┴──────────┘


```

---

## PART 3 — MODEL PROJECT STRUCTURE

```
authorised_capital_changes/
│
├── data/
│   ├── raw/
│   │   ├── SH7_Event1_2018.md
│   │   ├── SH7_Event2_2019.md
│   │   ├── SH7_Event3_2021.md
│   │   ├── SH7_Event4_2024.md
│   │   ├── BoardMeeting_Event1_2018.md
│   │   ├── EGM_Event1_2018.md
│   │   ├── MOA_Event1_2018.md
│   │   ├── BoardMeeting_Event2_2019.md
│   │   ├── EGM_Event2_2019.md
│   │   ├── MOA_Event2_2019.md
│   │   ├── BoardMeeting_Event3_2021.md
│   │   ├── EGM_Event3_2021.md
│   │   ├── MOA_Event3_2021.md
│   │   ├── BoardMeeting_Event4_2024.md
│   │   ├── EGM_Event4_2024.md
│   │   └── MOA_Event4_2024.md
│   │
│   └── outputs/
│       ├── extracted/
│       ├── capital_table.json
│       ├── capital_table.html
│       └── discrepancy_report.json
│
├── schemas/
│   ├── __init__.py
│   ├── document.py
│   ├── sh7.py
│   ├── attachment.py
│   ├── capital_event.py
│   ├── validation.py
│   ├── pipeline_state.py
│   └── output.py
│
├── pipeline/
│   ├── __init__.py
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── ingestion.py
│   │   ├── classifier.py
│   │   ├── relationship_resolver.py
│   │   ├── attachment_extractor.py
│   │   ├── sh7_extractor.py
│   │   ├── validator.py
│   │   ├── assembler.py
│   │   ├── narrative_generator.py
│   └── edges/
│       ├── __init__.py
│       └── routing.py
│
├── services/
│   ├── __init__.py
│   ├── llm_client.py
│   ├── document_parser.py
│   └── template_engine.py
│
├── api/
│   ├── __init__.py
│   ├── main.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── pipeline.py
│   │   └── results.py
│   └── models/
│       ├── __init__.py
│       ├── requests.py
│       └── responses.py
│
├── templates/
│   └── capital_table.html.j2
│
├── tests/
│   ├── unit/
│   │   ├── test_classifier.py
│   │   ├── test_sh7_extractor.py
│   │   ├── test_attachment_extractor.py
│   │   ├── test_validator.py
│   │   └── test_assembler.py
│   └── integration/
│       └── test_pipeline_e2e.py
│
├── config.py
├── requirements.txt
└── README.md
```

---

## PART 4 — SCHEMAS

### schemas/document.py

```python
from enum import Enum
from datetime import date
from pydantic import BaseModel


class DocumentType(str, Enum):
    SH7 = "SH7"
    PAS3 = "PAS3"
    BOARD_MEETING_RESOLUTION = "BOARD_MEETING_RESOLUTION"
    EGM_RESOLUTION = "EGM_RESOLUTION"
    EGM_NOTICE = "EGM_NOTICE"
    MOA = "MOA"
    LIST_OF_ALLOTTEES = "LIST_OF_ALLOTTEES"
    UNKNOWN = "UNKNOWN"


class OfficialStatus(str, Enum):
    OFFICIAL = "OFFICIAL"
    CERTIFIED_COPY = "CERTIFIED_COPY"
    DRAFT = "DRAFT"
    UNCONFIRMED = "UNCONFIRMED"


class FileMetadata(BaseModel):
    filename: str
    filepath: str
    raw_content: str
    file_size_bytes: int


class ClassifiedDocument(BaseModel):
    file_metadata: FileMetadata
    document_type: DocumentType
    official_status: OfficialStatus
    classification_method: str          # "rule_based" or "llm_fallback"
    classification_confidence: float
    event_date_hint: date | None
    cin_hint: str | None
    requires_human_review: bool
    review_reason: str | None


class DocumentGroup(BaseModel):
    event_index: int                    # 1-based, assigned after chronological sort
    sh7: ClassifiedDocument
    board_resolution: ClassifiedDocument | None
    egm_resolution: ClassifiedDocument | None
    moa: ClassifiedDocument | None
    unmatched_attachment_refs: list[str]
```

### schemas/sh7.py

```python
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
    # difference_addition is NOT stored here.
    # It is extracted only during Node 6 validation from Field 6
    # for the arithmetic check, then discarded.

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
```

### schemas/attachment.py 

```python
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
```

### schemas/capital_event.py

```python
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
```

### schemas/validation.py

```python
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
```

### schemas/output.py

```python
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
    documents_in_human_review: int
    flags: list[FlagEntry]
    arithmetic_failures: list[dict]
    continuity_failures: list[dict]
    cross_document_conflicts: list[dict]
    duplicate_sh7s: list[dict]
    unmatched_attachments: dict[str, list[str]]
    blocked_sh7s: list[dict]
    human_review_items: list[dict]
    corroborations: list[dict]
    # corroboration entry shape:
    # { check, result ("AGREED"|"DISAGREED"), moa_figure,
    #   sh7_figure, source_moa, source_sh7, note (only if DISAGREED) }
```

### schemas/pipeline_state.py

```python
from typing import TypedDict
from .document import FileMetadata, ClassifiedDocument, DocumentGroup
from .sh7 import SH7Extraction
from .attachment import BoardResolutionExtraction, EGMResolutionExtraction, MOAExtraction
from .capital_event import CapitalTableRow
from .validation import ValidationReport
from .output import DiscrepancyReport


class AttachmentExtractionBundle(TypedDict):
    event_index: int
    sh7_filename: str
    board_resolution: BoardResolutionExtraction | None
    egm_resolution: EGMResolutionExtraction | None
    moa: MOAExtraction | None


class PipelineState(TypedDict):
    run_id: str
    input_folder: str
    started_at: str
    raw_files: list[FileMetadata]
    classified_docs: list[ClassifiedDocument]
    sh7_documents: list[ClassifiedDocument]
    non_sh7_documents: list[ClassifiedDocument]
    unclassified_documents: list[ClassifiedDocument]
    document_groups: list[DocumentGroup]
    unmatched_attachment_refs: dict[str, list[str]]
    attachment_bundles: list[AttachmentExtractionBundle]
    extracted_sh7s: list[SH7Extraction]
    sh7_extraction_errors: list[dict]
    validation_reports: list[ValidationReport]
    sh7s_blocked_by_validation: list[str]
    sh7s_passed_validation: list[str]
    capital_table_rows: list[CapitalTableRow]
    final_table_rows: list[CapitalTableRow]
    discrepancy_report: DiscrepancyReport
    human_review_queue: list[ClassifiedDocument]
    human_review_resolved: list[ClassifiedDocument]
    human_review_required: bool
    pipeline_errors: list[dict]
    completed_stages: list[str]
```

---

## PART 5 — PIPELINE NODES

### Node 1 — Ingestion (ingestion.py)

No LLM. Pure file I/O.

Input: `state["input_folder"]`

Processing:
- Iterate all `.md` files in the flat input folder
- For each file create `FileMetadata` with filename, filepath, raw_content, file_size_bytes
- If a file cannot be read, append `{filename, error, stage: "ingestion"}` to `state["pipeline_errors"]` and continue

Output: `state["raw_files"]`

---

### Node 2 — Classifier (classifier.py)

Input: `state["raw_files"]`

Pass 1 — Rule-based (no LLM):

```
Priority 1 — Filename (confidence 0.92):
    contains "SH7" or "SH-7"           → SH7
    contains "BoardMeeting"             → BOARD_MEETING_RESOLUTION
    contains "EGM" and not "Notice"     → EGM_RESOLUTION
    contains "EGM" and "Notice"         → EGM_NOTICE
    contains "MOA"                      → MOA
    contains "PAS3" or "PAS-3"         → PAS3
    contains "Allottees"                → LIST_OF_ALLOTTEES

Priority 2 — Content keywords (confidence 0.87):
    "FORM NO. SH-7"                     → SH7
    "Notice to Registrar" +
    "alteration of share capital"       → SH7
    "FORM NO. PAS-3"                    → PAS3
    "Return of Allotment"               → PAS3
    "CERTIFIED TRUE COPY" +
    "BOARD OF DIRECTORS"                → BOARD_MEETING_RESOLUTION
    "EXTRA ORDINARY GENERAL"            → EGM_RESOLUTION
    "Memorandum of Association" +
    "Clause V"                          → MOA

Priority 3 — Official status (independent of type):
    SRN pattern H\d{8} present         → OFFICIAL
    "CERTIFIED TRUE COPY" present       → CERTIFIED_COPY
    neither                             → DRAFT
```

Pass 2 — LLM fallback (only if confidence < 0.85):

```
System: You are a document classifier for Indian MCA corporate filings.
        Classify into exactly one type:
        SH7, PAS3, BOARD_MEETING_RESOLUTION, EGM_RESOLUTION, EGM_NOTICE,
        MOA, LIST_OF_ALLOTTEES, UNKNOWN
        Determine official status: OFFICIAL, CERTIFIED_COPY, DRAFT, UNCONFIRMED
        Return JSON only via tool_use. No explanation. No preamble.

User:   [first 500 tokens of document content]

Tool:   { document_type, official_status, confidence, reason }
```

Routing after classification:
- confidence < 0.6 → `unclassified_documents` + `human_review_queue`
- document_type == SH7 → `sh7_documents`
- all others → `non_sh7_documents`

Duplicate SH-7 pre-check:
- After all SH-7s classified, extract `event_date_hint` from each
- If two SH-7s share same `event_date_hint`, move both to `human_review_queue` with `review_reason: "DUPLICATE_MEETING_DATE"`, remove from `sh7_documents`, log to `pipeline_errors`
- Terminate with error if `sh7_documents` is empty after deduplication

Output: `classified_docs`, `sh7_documents`, `non_sh7_documents`, `unclassified_documents`

---

### Node 3 — Relationship Resolver (relationship_resolver.py)

Input: `state["sh7_documents"]`, `state["non_sh7_documents"]`

For each SH-7:

Step 1: Parse Field 12 of SH-7 raw content. Extract all filename strings from the attachments table. Store as raw strings exactly as written.

Step 2: For each filename string, attempt match against `non_sh7_documents`:
- Primary: exact filename match (case-insensitive)
- Secondary: strip extension, compare stems
- No match: add to `unmatched_attachment_refs[sh7_filename]`

Step 3: From matched documents, assign by type:
- BOARD_MEETING_RESOLUTION → `group.board_resolution`
- EGM_RESOLUTION → `group.egm_resolution`
- MOA → `group.moa`
- Any other matched type: logged, not used

Step 4: NO independent MOA search. MOA linked only if explicitly listed in Field 12.

Step 5: Assign `event_index` from filename event number if present. Otherwise 0 — assembler sorts later.

Output: `document_groups`, `unmatched_attachment_refs`

---

### Node 4 — Attachment Extractor (attachment_extractor.py)

Input: `state["document_groups"]`

For each DocumentGroup, run one LLM call per present attachment.

**Board Resolution prompt:**

```
System: You are an expert in Indian corporate law and MCA board resolutions.
        Extract only:
        - Date of the board meeting
        - Capital amount the board resolved to increase authorised capital to
        - Resolution type (Ordinary or Special)
        - CIN of the company
        Never infer. If not explicitly stated, set to null.
        Return JSON only via tool_use.

User:   [full board resolution content]
Tool:   BoardResolutionExtraction schema
```

**EGM/AGM Resolution prompt:**

```
System: You are an expert in Indian corporate law and MCA EGM/AGM resolutions.
        Extract only:
        - Date of the meeting
        - Whether this is an EGM or AGM. Populate meeting_type ONLY if the
          word "EGM" or "AGM" appears literally in the document body.
          Never infer from filename. Never infer from context.
        - Capital amount the members resolved to increase to
        - CIN of the company
        Never infer. If not explicitly stated, set to null.
        Return JSON only via tool_use.

User:   [full EGM/AGM resolution content]
Tool:   EGMResolutionExtraction schema
```

**MOA prompt:**

```
System: You are an expert in Indian corporate law and Memoranda of Association.
        Extract only from Clause V:
        - Total authorised capital amount in rupees
        - Number of equity shares
        - Nominal value per equity share
        - Number of preference shares if present (null if not present)
        - Nominal value per preference share if present (null if not present)
        - CIN if present
        Never infer. If not explicitly stated, set to null.
        Return JSON only via tool_use.

User:   [full MOA content]
Tool:   MOAExtraction schema
```

Output: `attachment_bundles`

---

### Node 5 — SH-7 Extractor (sh7_extractor.py)

Input: `state["document_groups"]` (sh7 field only)

```
System: You are an expert in Indian corporate law and MCA Form SH-7 filings.
        Extract structured data exactly as it appears. Rules strictly enforced:
        1.  Never infer, calculate, or fill gaps with assumptions.
        2.  If a field is missing or ambiguous, set to null and add field
            name to unconfirmed_fields.
        3.  Extract existing_authorised_capital from "Existing (in Rs.)"
            row under Field 4(a)(i).
        4.  Extract revised_authorised_capital from "Revised (in Rs.)"
            row under Field 4(a)(i).
        5.  Do NOT extract difference_addition — it is not part of the schema.
        6.  Extract authorised capital breakdown from Section 9(a) ONLY.
            Do NOT extract Sections 9(b), 9(c), or 9(d).
        7.  Extract attachment filenames from Field 12 exactly as written.
            Do not clean, normalise, or interpret these strings.
        8.  Extract SRN from "eForm Service request number" in the office
            use footer at the bottom of the form.
        9.  All monetary amounts as plain decimal numbers in rupees.
            No commas, no currency symbols, no formatting.
        10. meeting_type is NOT extracted from the SH-7. It is populated
            by Node 4 from the EGM/AGM resolution document body.
        Return JSON only via tool_use.

User:   [full SH-7 content]
Tool:   SH7Extraction schema
```

On extraction failure: append `{filename, error_message}` to `sh7_extraction_errors`. Continue.
Terminate with error if zero successful extractions.

Output: `extracted_sh7s`, `sh7_extraction_errors`

---

### Node 6 — Validator (validator.py)

Input: `state["extracted_sh7s"]`, `state["attachment_bundles"]`

Step 1: Sort all extracted SH-7s chronologically by `meeting_date`.

Step 2 — Arithmetic Check (per SH-7):

Extract `difference_addition` from Field 6 (Total addition line) of the SH-7 raw content. Used only here — not stored in state after this node.

Check: `existing_authorised_capital + difference_addition == revised_authorised_capital`

If fails: non-blocking flag. Row still assembled using `revised_authorised_capital`. Flag added to `ValidationReport.non_blocking_flags`.

Step 3 — Continuity Check (across SH-7s):

Event 1 (index 0): `existing_authorised_capital` is the ground truth anchor. No upstream check.

Optional MOA corroboration for Event 1 only:
```python
if moa_bundle and moa_bundle.moa and moa_bundle.moa.incorporation_capital:
    agreed = (moa_bundle.moa.incorporation_capital ==
              sorted_sh7s[0].existing_authorised_capital)
    discrepancy_report.corroborations.append({
        "check": "MOA Clause V vs SH-7 Event 1 existing capital",
        "result": "AGREED" if agreed else "DISAGREED",
        "moa_figure": str(moa_bundle.moa.incorporation_capital),
        "sh7_figure": str(sorted_sh7s[0].existing_authorised_capital),
        "source_moa": moa_bundle.moa.source_filename,
        "source_sh7": sorted_sh7s[0].srn,
        "note": "Non-blocking. Does not affect output table." if not agreed else None
    })
# If MOA not available: no corroboration entry, no flag raised
```

Events 2–N (index 1 onward):
```
expected_from = sorted_sh7s[i-1].revised_authorised_capital
actual_from   = sorted_sh7s[i].existing_authorised_capital

If expected_from != actual_from:
    → blocking error
    → add sh7_filename to sh7s_blocked_by_validation
    → add to ValidationReport.blocking_errors
```

Step 4 — Cross-Document Check (per DocumentGroup):

**Date check:**
```
Compare SH7.meeting_date vs BoardResolution.meeting_date
                          vs EGMResolution.meeting_date

If SH-7 disagrees with one attachment but agrees with another:
    → non-blocking flag with flag_code assigned sequentially
    → add to ValidationReport.non_blocking_flags

If SH-7 disagrees with ALL available attachments:
    → blocking error
    → route to human_review_queue
    → add to sh7s_blocked_by_validation
```

**Capital amount check:**
```
Compare SH7.revised_authorised_capital vs BoardResolution.resolved_capital_amount
                                        vs EGMResolution.resolved_capital_amount

Same logic as date check above.
```

**Meeting type naming rule — enforced here:**
```
ClassifiedDocument.document_type is determined from filename (structural type).
EGMResolutionExtraction.meeting_type is determined from document body (content).
These are NEVER compared against each other.
A file named EGM_EventN whose body says "AGM" is valid.
meeting_type = "AGM" is the correct extracted value.
No flag is raised.
```

Step 5 — Definitive Duplicate Check:

Using extracted `meeting_date` values (more reliable than hints from Node 2). If duplicates found: both to `human_review_queue`, both to `sh7s_blocked_by_validation`.

Flag code assignment: assign `FLAG_001`, `FLAG_002` etc. sequentially across all events in chronological order.

Output: `validation_reports`, `sh7s_blocked_by_validation`, `sh7s_passed_validation`

---

### Node 7 — Assembler (assembler.py)

Input: `state["extracted_sh7s"]`, `state["attachment_bundles"]`, `state["validation_reports"]`

Filter to `sh7s_passed_validation` only. Blocked SH-7s produce no rows.

**Helper — format_capital_narrative:**

```python
def format_capital_narrative(
    total_amount: Decimal,
    equity_count: int | None,
    equity_nominal: Decimal | None,
    preference_count: int | None = None,
    preference_nominal: Decimal | None = None
) -> str:
    """
    All amounts formatted using Indian number system (lakh/crore).
    ₹1,50,000 not ₹150,000
    ₹50,00,000 not ₹5,000,000
    ₹2,00,00,000 not ₹20,000,000

    Case 1 — equity only, full breakdown available:
        "₹1,50,000 divided into 15,000 Equity Shares of ₹10 each"

    Case 2 — equity + preference, full breakdown available:
        "₹2,00,00,000 divided into 18,00,000 Equity Shares of ₹10 each
         and 2,00,000 Preference Shares of ₹10 each"
        Equity always stated first. Preference always second.
        Joined by the word "and".

    Case 3 — breakdown unavailable (equity_count is None):
        "₹X (share breakdown not determinable — see footnote)"
    """
```

**Helper — compute_prechange_breakdown:**

```python
# INVOCATION RULE:
# Called ONLY when building Row 0 (On Incorporation).
# NEVER called for Rows 1–N.
# For Rows 1–N: authorised_from.value = rows[i-1].authorised_to.value
# This is a direct string copy. No computation. No derivation. No LLM.

def compute_prechange_breakdown(
    existing_total: Decimal,
    nominal_per_share: Decimal,
    post_change_preference_count: int | None,
    source_sh7_filename: str
) -> tuple[int, str] | tuple[None, str]:
    """
    Guard — multi-class pre-change capital:
    If post_change_preference_count > 0, preference shares exist in
    post-change capital. Pre-change equity count cannot be safely derived
    by dividing total by equity nominal alone. Return None.
    """
    if post_change_preference_count is not None and post_change_preference_count > 0:
        return None, (
            "Pre-change share breakdown cannot be derived arithmetically — "
            "preference shares present in post-change capital suggest mixed "
            "share classes may exist in pre-change capital. "
            f"Source: {source_sh7_filename} Section 9(a)"
        )

    if nominal_per_share == 0:
        return None, "Cannot compute: nominal value per share is zero"

    quotient = existing_total / nominal_per_share
    if quotient != int(quotient):
        return None, (
            f"Existing capital {existing_total} is not exactly divisible "
            f"by nominal value {nominal_per_share} — breakdown cannot be "
            f"derived arithmetically"
        )

    return int(quotient), (
        f"Share count derived arithmetically: existing capital ÷ "
        f"nominal value per share from Section 9(a) of {source_sh7_filename}"
    )
```

**Row 0 — On Incorporation:**

```python
sh7_e1 = sorted_sh7s[0]
sh7_e1_filename = sh7_e1_doc.file_metadata.filename

computed_count, source_note = compute_prechange_breakdown(
    existing_total=sh7_e1.existing_authorised_capital,
    nominal_per_share=sh7_e1.authorised_capital.breakdown.equity_nominal_per_share,
    post_change_preference_count=sh7_e1.authorised_capital.breakdown.preference_shares_count,
    source_sh7_filename=sh7_e1_filename
)

row_0 = CapitalTableRow(
    row_number=0,
    meeting_date=FieldValue(
        value="On incorporation",
        confirmed=True,
        source_document=sh7_e1_filename,
        source_field_machine="Field 4(a)(i) — Existing",
        source_field_human="Existing authorised capital before first event, "
                           "used as incorporation capital"
    ),
    authorised_from=FieldValue(
        value=None,           # display: "-"
        confirmed=True,
        source_document=sh7_e1_filename,
        source_field_machine=None,
        source_field_human=None
    ),
    authorised_to=FieldValue(
        value=format_capital_narrative(
            total_amount=sh7_e1.existing_authorised_capital,
            equity_count=computed_count,
            equity_nominal=sh7_e1.authorised_capital.breakdown.equity_nominal_per_share
            # preference not present at incorporation in this dataset
        ),
        confirmed=computed_count is not None,
        source_document=sh7_e1_filename,
        source_field_machine="Field 4(a)(i) — Existing + Section 9(a) nominal value",
        source_field_human=source_note,
        flag_code=None if computed_count is not None else "FLAG_BREAKDOWN_UNDERIVABLE",
        flag_message=None if computed_count is not None else source_note
    ),
    meeting_type=FieldValue(
        value=None,           # display: "-"
        confirmed=True,       # no flag — no meeting occurred at incorporation
        source_document=None,
        source_field_machine=None,
        source_field_human=None
    ),
    source_srn=None,
    source_sh7_filename=sh7_e1_filename,
    source_filing_date=None,
    has_flags=computed_count is None,
    flag_count=1 if computed_count is None else 0,
    flags=["FLAG_BREAKDOWN_UNDERIVABLE"] if computed_count is None else []
)
```

**Rows 1–N — one per SH-7:**

```python
rows = [row_0]

for i, sh7 in enumerate(sorted_sh7s):
    bundle = get_bundle_for_sh7(sh7, attachment_bundles)
    val_report = get_validation_report_for(sh7, validation_reports)
    egm = bundle["egm_resolution"]
    sh7_filename = get_sh7_filename(sh7, document_groups)

    date_flag = get_cross_doc_flag(val_report, "DATE")
    capital_flag = get_cross_doc_flag(val_report, "CAPITAL_AMOUNT")

    # meeting_date
    meeting_date_fv = FieldValue(
        value=sh7.meeting_date,     # date object — formatted to string in Node 8
        confirmed=True,
        source_document=sh7_filename,
        source_field_machine="Field 4",
        source_field_human="Date of members' meeting, Field 4",
        flag_code=date_flag.flag_code if date_flag else None,
        flag_message=date_flag.full_message if date_flag else None
    )

    # authorised_from — ALWAYS direct string copy from previous row's To
    # No computation. No re-extraction. No LLM.
    authorised_from_fv = FieldValue(
        value=rows[i].authorised_to.value,
        confirmed=True,
        source_document=sh7_filename,
        source_field_machine="Field 4(a)(i) — Existing",
        source_field_human="Existing authorised capital before this event"
    )

    # authorised_to
    authorised_to_fv = FieldValue(
        value=format_capital_narrative(
            total_amount=sh7.revised_authorised_capital,
            equity_count=sh7.authorised_capital.breakdown.equity_shares_count,
            equity_nominal=sh7.authorised_capital.breakdown.equity_nominal_per_share,
            preference_count=sh7.authorised_capital.breakdown.preference_shares_count,
            preference_nominal=sh7.authorised_capital.breakdown.preference_nominal_per_share
        ),
        confirmed=True,
        source_document=sh7_filename,
        source_field_machine="Section 9(a)",
        source_field_human="Authorised capital after change, Section 9(a)",
        flag_code=capital_flag.flag_code if capital_flag else None,
        flag_message=capital_flag.full_message if capital_flag else None
    )

    # meeting_type — confirmed from EGM/AGM resolution body if available
    if egm and egm.meeting_type:
        meeting_type_fv = FieldValue(
            value=egm.meeting_type,     # "EGM" or "AGM" from document body
            confirmed=True,
            source_document=egm.source_filename,
            source_field_machine="EGM/AGM Resolution operative clause",
            source_field_human="Meeting type confirmed from EGM/AGM resolution document"
        )
    else:
        meeting_type_fv = FieldValue(
            value=None,
            confirmed=False,
            source_document=None,
            source_field_machine=None,
            source_field_human=None,
            flag_code="FLAG_MEETING_TYPE_UNCONFIRMED",
            flag_message="AGM/EGM could not be confirmed — EGM/AGM resolution "
                         "document not available or did not state meeting type explicitly"
        )

    row_flags = [f for f in [
        meeting_date_fv.flag_code,
        authorised_to_fv.flag_code,
        meeting_type_fv.flag_code
    ] if f is not None]

    rows.append(CapitalTableRow(
        row_number=i + 1,
        meeting_date=meeting_date_fv,
        authorised_from=authorised_from_fv,
        authorised_to=authorised_to_fv,
        meeting_type=meeting_type_fv,
        source_srn=sh7.srn,
        source_sh7_filename=sh7_filename,
        source_filing_date=sh7.filing_date,
        has_flags=len(row_flags) > 0,
        flag_count=len(row_flags),
        flags=row_flags
    ))
```

Output: `capital_table_rows`

---

### Node 8 — Narrative Generator (narrative_generator.py)

Input: `state["capital_table_rows"]`, `state["validation_reports"]`

**Step 0 — Date formatting (runs first):**

```python
# For every row where meeting_date.value is a date object (Rows 1–N):
#     display_date = date_obj.strftime("%-d %B %Y")
#     e.g. date(2018, 3, 22)  → "22 March 2018"
#     e.g. date(2021, 9, 10)  → "10 September 2021"
#     e.g. date(2024, 3, 28)  → "28 March 2024"
#     This is rendering-only. The date object in FieldValue is not mutated.
#
# For Row 0:
#     meeting_date.value is the literal string "On incorporation"
#     Do not pass through strftime. Write to template as-is.
```

**Step 1 — Collect and number all flags:**

Iterate all rows top-to-bottom. Within each row iterate fields left-to-right in this order: meeting_date, authorised_from, authorised_to, meeting_type. Collect every non-null flag_code in the order encountered. Assign sequential footnote numbers [1], [2], etc.

**Step 2 — Build FlagEntry list** for discrepancy report. One entry per unique flag_code.

**Step 3 — Assemble DiscrepancyReport** with all counts, flags, arithmetic failures, continuity failures, cross-document conflicts, duplicate checks, unmatched attachments, blocked SH-7s, human review items, corroborations.

**Step 4 — Write outputs:**
- `final_table_rows` → `data/outputs/capital_table.json`
- `discrepancy_report` → `data/outputs/discrepancy_report.json`
- Rendered HTML → `data/outputs/capital_table.html` via Jinja2 template

Output: `final_table_rows`, `discrepancy_report`

---

## PART 6 — ROUTING LOGIC (routing.py)

```
ingestion_node
    → classifier_node (always)

classifier_node
    → [terminate with error] if sh7_documents empty after dedup
    → relationship_resolver_node (sh7_documents)
    → [log non_sh7_documents, continue]

relationship_resolver_node
    → attachment_extractor_node (always)

attachment_extractor_node
    → sh7_extractor_node (always)

sh7_extractor_node
    → [terminate with error] if zero successful extractions
    → validator_node (at least one extraction succeeded)

validator_node
    → [terminate with partial error] if zero passed validation
    → assembler_node (at least one passed)

assembler_node
    → narrative_generator_node (always)

narrative_generator_node
    → output_writer (always)
```

---

## PART 7 — OUTPUT AND RENDERING

### Jinja2 Template Rules (capital_table.html.j2)

Column 1 — Date of Shareholder's Meeting:
- Row 0: literal string "On incorporation"
- Rows 1–N: formatted date string "DD Month YYYY" from Node 8 Step 0
- If flag_code present: append ` ⚠️ [N]` where N is footnote number

Column 2 — From:
- Row 0: literal "-"
- Rows 1–N: `authorised_from.value`
- Flags on From column are not expected in current design

Column 3 — To:
- All rows: `authorised_to.value`
- If flag_code present: append ` ⚠️ [N]`

Column 4 — AGM/EGM:
- Row 0: literal "-"
- Rows 1–N: `meeting_type.value` if confirmed, else flag
- If flag_code present: append ` ⚠️ [N]`

Below table: numbered footnote list. Each entry contains:
- Flag number, flag message, source document, conflicting document if present, recommended action

### Indian Number Formatting

```
₹1,50,000        not ₹150,000
₹3,00,000        not ₹300,000
₹50,00,000       not ₹5,000,000
₹2,00,00,000     not ₹20,000,000
₹10,00,00,000    not ₹100,000,000
```

Implement as a standalone utility function in `services/document_parser.py` or a dedicated `utils/formatting.py`. Used by `format_capital_narrative` in the assembler and by the Jinja2 template filter.

---

## PART 8 — FASTAPI ROUTES

```
POST   /api/v1/pipeline/run
       Body:     { "input_folder": "/path/to/folder", "run_id": "optional" }
       Response: { "run_id": "abc123", "status": "started", "started_at": "..." }

GET    /api/v1/pipeline/status/{run_id}
       Response: { "status": "running|completed|failed|partial",
                   "completed_stages": [...],
                   "human_review_required": bool,
                   "pipeline_errors": [...] }

GET    /api/v1/results/{run_id}/table
       Response: { "capital_table": [...CapitalTableRow],
                   "flags": [...FlagEntry] }

GET    /api/v1/results/{run_id}/discrepancy-report
       Response: { "discrepancy_report": {...DiscrepancyReport} }

GET    /api/v1/results/{run_id}/html
       Response: rendered HTML (Content-Type: text/html)

POST   /api/v1/pipeline/{run_id}/human-review/resolve
       Body:     { "filename": "...",
                   "resolved_type": "SH7",
                   "resolved_status": "OFFICIAL" }
       Response: { "run_id": "...", "rerun_triggered": true }
       # Triggers fresh pipeline run with resolved classification injected
```

---

## PART 9 — LOGGING 

** Create a new file: `authorised_capital_changes/logging_config.py`**
- `configure_logging()` — call it once at startup. It attaches two handlers to the **root logger**:
  - `StreamHandler` → terminal (same as before)
  - `TimedRotatingFileHandler` → `data/logs/pipeline_<YYYY-MM-DD>.log`
- Rotates at midnight, keeps **30 daily files**.
- Format: `2026-05-24 07:35:01 | INFO     | nodes.validator | Validator started | sh7_count=4`

**`run_pipeline.py`** — replace `logging.basicConfig()` with `configure_logging()`

**`api/main.py`** — add a `lifespan` startup hook that calls `configure_logging()` when uvicorn starts

---

### Log file location
```
Project/
└── data/
    └── logs/
        ├── pipeline_2026-05-24.log   ← today
        ├── pipeline_2026-05-23.log   ← yesterday (auto-rotated)
        └── ...                       ← up to 30 days retained
```

Because every node already uses `logging.getLogger(__name__)`, **no changes are needed inside any node**

---
