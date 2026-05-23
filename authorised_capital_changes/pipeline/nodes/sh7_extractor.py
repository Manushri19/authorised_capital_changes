"""
Node 5 — SH-7 Extractor (sh7_extractor.py)
============================================
Runs one Gemini function-calling extraction per SH-7 document
using only the sh7 field from each DocumentGroup.

Extraction rules (system prompt):
  1.  Never infer, calculate, or fill gaps.
  2.  Missing / ambiguous → null + add to unconfirmed_fields.
  3.  existing_authorised_capital ← "Existing (in Rs.)" row, Field 4(a)(i).
  4.  revised_authorised_capital  ← "Revised (in Rs.)"  row, Field 4(a)(i).
  5.  difference_addition NOT extracted (schema does not hold it).
  6.  Authorised capital breakdown ← Section 9(a) ONLY.
      Sections 9(b), 9(c), 9(d) are ignored.
  7.  attachment_filenames_raw ← Field 12, raw strings, no normalisation.
  8.  srn ← "eForm Service request number" in the office-use footer.
  9.  All monetary amounts: plain decimal numbers in rupees (no commas / symbols).
  10. meeting_type is NOT extracted from SH-7.

On per-document failure: append {filename, error_message} to sh7_extraction_errors.
Terminates with ValueError if zero successful extractions.

Output: state["extracted_sh7s"], state["sh7_extraction_errors"]
"""

from __future__ import annotations

import logging
import os
from decimal import Decimal, InvalidOperation
from datetime import date, datetime
from typing import Any

from google.genai import types

from authorised_capital_changes.schemas.document import DocumentGroup
from authorised_capital_changes.schemas.sh7 import (
    AuthorisedCapitalBlock,
    ShareBreakdown,
    SH7Extraction,
)
from authorised_capital_changes.schemas.pipeline_state import PipelineState
from authorised_capital_changes.services.llm_client import default_llm_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GEMINI_MODEL: str = os.getenv("EXTRACTOR_GEMINI_MODEL", "gemini-2.5-flash")

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SH7_SYSTEM = """\
You are an expert in Indian corporate law and MCA Form SH-7 filings.
Extract structured data exactly as it appears in the document. Rules:

1.  Never infer, calculate, or fill gaps with assumptions.
2.  If a field is missing or ambiguous, set it to null and add the field name
    to unconfirmed_fields.
3.  Extract existing_authorised_capital from the "Existing (in Rs.)" row in
    the table under Field 4(a)(i).
4.  Extract revised_authorised_capital from the "Revised (in Rs.)" row in
    the table under Field 4(a)(i).
5.  Do NOT extract difference_addition — it is not part of the schema.
6.  Extract the authorised capital breakdown from Section 9(a) ONLY.
    Do NOT read Sections 9(b), 9(c), or 9(d).
7.  Extract attachment filenames from Field 12 / ## Attachments section
    exactly as written. Do not clean, normalise, or interpret.
    Only include strings that look like actual file names (contain a dot
    followed by an extension). Skip boilerplate labels.
8.  Extract srn from the "eForm Service request number (SRN)" line in the
    "For office use only" footer.
9.  All monetary amounts must be plain decimal numbers in rupees.
    No commas, no currency symbols, no formatting (e.g. 5000000 not 50,00,000).
10. meeting_type is NOT extracted from the SH-7 form.

Return your answer ONLY via the extract_sh7 tool call.\
"""

# ---------------------------------------------------------------------------
# Tool schema
# ---------------------------------------------------------------------------

_SH7_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="extract_sh7",
            description="Extract structured fields from an Indian MCA Form SH-7.",
            parameters={
                "type": "OBJECT",
                "properties": {
                    # ---- Identity ----
                    "cin": {
                        "type": "STRING",
                        "description": "Corporate Identity Number from Field 1(a).",
                    },
                    "company_name": {
                        "type": "STRING",
                        "description": "Company name from Field 2(a).",
                    },
                    "registered_address": {
                        "type": "STRING",
                        "description": "Registered office address from Field 2(b).",
                    },
                    "email": {
                        "type": "STRING",
                        "description": "Email address from Field 2(c).",
                    },
                    # ---- Event ----
                    "purpose": {
                        "type": "STRING",
                        "description": "Purpose of the form from Field 3 (the selected option).",
                    },
                    "meeting_date": {
                        "type": "STRING",
                        "description": "Date of the members meeting from Field 4, DD/MM/YYYY or YYYY-MM-DD.",
                    },
                    "resolution_type": {
                        "type": "STRING",
                        "enum": ["Ordinary", "Special"],
                        "description": "Ordinary or Special resolution from Field 4.",
                    },
                    # ---- Capital change Field 4(a)(i) ----
                    "existing_authorised_capital": {
                        "type": "STRING",
                        "description": (
                            "Existing capital in Rs from the 'Existing (in Rs.)' row "
                            "under Field 4(a)(i). Plain decimal number, no commas."
                        ),
                    },
                    "revised_authorised_capital": {
                        "type": "STRING",
                        "description": (
                            "Revised capital in Rs from the 'Revised (in Rs.)' row "
                            "under Field 4(a)(i). Plain decimal number, no commas."
                        ),
                    },
                    "difference_addition": {
                        "type": "STRING",
                        "description": (
                            "Difference (addition) capital in Rs from the 'Difference (addition) (in Rs.)' row "
                            "under Field 4(a)(i) or 'Total addition' in Field 6. Plain decimal number, no commas."
                        ),
                    },
                    # ---- Section 9(a) authorised capital breakdown ----
                    "section_9a_total_amount": {
                        "type": "STRING",
                        "description": (
                            "Total authorised capital from Section 9(a) label "
                            "(e.g. '50,00,000.00'). Plain decimal, no commas."
                        ),
                    },
                    "section_9a_equity_shares_count": {
                        "type": "INTEGER",
                        "description": "Number of equity shares from Section 9(a) table.",
                    },
                    "section_9a_equity_nominal_per_share": {
                        "type": "STRING",
                        "description": "Nominal amount per equity share from Section 9(a). Plain decimal.",
                    },
                    "section_9a_equity_total_amount": {
                        "type": "STRING",
                        "description": "Total amount of equity shares from Section 9(a). Plain decimal.",
                    },
                    "section_9a_preference_shares_count": {
                        "type": "INTEGER",
                        "description": "Number of preference shares from Section 9(a). 0 if none.",
                    },
                    "section_9a_preference_nominal_per_share": {
                        "type": "STRING",
                        "description": "Nominal amount per preference share from Section 9(a). Plain decimal. Null if none.",
                    },
                    "section_9a_preference_total_amount": {
                        "type": "STRING",
                        "description": "Total amount of preference shares from Section 9(a). Plain decimal. Null if none.",
                    },
                    "section_9a_unclassified_shares_count": {
                        "type": "INTEGER",
                        "description": "Number of unclassified shares from Section 9(a). Null if absent.",
                    },
                    "section_9a_unclassified_total_amount": {
                        "type": "STRING",
                        "description": "Total amount of unclassified shares from Section 9(a). Plain decimal. Null if absent.",
                    },
                    # ---- Filing footer ----
                    "srn": {
                        "type": "STRING",
                        "description": (
                            "eForm Service Request Number from 'For office use only' footer. "
                            "Null if not present."
                        ),
                    },
                    "filing_date": {
                        "type": "STRING",
                        "description": "eForm filing date from footer, DD/MM/YYYY or YYYY-MM-DD. Null if absent.",
                    },
                    # ---- Stamp duty Field 11 ----
                    "stamp_duty_state": {
                        "type": "STRING",
                        "description": "State/UT for stamp duty from Field 11(a). Null if absent.",
                    },
                    "stamp_duty_amount": {
                        "type": "STRING",
                        "description": "Amount of stamp duty in rupees from Field 11. Plain decimal. Null if absent.",
                    },
                    # ---- Attachments Field 12 ----
                    "attachment_filenames_raw": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": (
                            "Filenames from the ## Attachments section exactly as written "
                            "(include extension). Exclude boilerplate labels."
                        ),
                    },
                    # ---- Quality ----
                    "extraction_confidence": {
                        "type": "NUMBER",
                        "description": "Overall extraction confidence [0,1].",
                    },
                    "unconfirmed_fields": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "Names of fields that are uncertain.",
                    },
                    "extraction_errors": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "Any errors encountered during extraction.",
                    },
                },
                "required": [
                    "cin", "company_name", "registered_address", "email",
                    "purpose", "meeting_date", "resolution_type",
                    "existing_authorised_capital", "revised_authorised_capital",
                    "difference_addition", "section_9a_total_amount",
                    "attachment_filenames_raw",
                    "extraction_confidence", "unconfirmed_fields", "extraction_errors",
                ],
            },
        )
    ]
)

# ---------------------------------------------------------------------------
# Safe type converters
# ---------------------------------------------------------------------------

def _dec(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        cleaned = str(value).replace(",", "").strip()
        if not cleaned or cleaned.lower() in ("null", "none", "-", ""):
            return None
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def _dec_required(value: Any, field_name: str, errors: list[str]) -> Decimal:
    """Convert to Decimal; on failure record error and return Decimal(0)."""
    result = _dec(value)
    if result is None:
        errors.append(f"Could not parse required decimal field '{field_name}': {value!r}")
        return Decimal("0")
    return result


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    s = str(value).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _parse_date_required(value: Any, field_name: str, errors: list[str]) -> date:
    result = _parse_date(value)
    if result is None:
        errors.append(f"Could not parse required date field '{field_name}': {value!r}")
        return date(1970, 1, 1)
    return result

# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

def _call_llm(content: str) -> dict | None:
    return default_llm_client.extract_structured_data(
        system_instruction=_SH7_SYSTEM,
        user_prompt=content,
        tool=_SH7_TOOL,
        tool_name="extract_sh7"
    )

# ---------------------------------------------------------------------------
# Build SH7Extraction from raw LLM args
# ---------------------------------------------------------------------------

def build_extraction(filename: str, args: dict) -> SH7Extraction:
    parse_errors: list[str] = list(args.get("extraction_errors") or [])
    unconfirmed: list[str] = list(args.get("unconfirmed_fields") or [])

    # -- Section 9(a) breakdown --
    breakdown = ShareBreakdown(
        equity_shares_count=_int_or_none(args.get("section_9a_equity_shares_count")),
        equity_nominal_per_share=_dec(args.get("section_9a_equity_nominal_per_share")),
        equity_total_amount=_dec(args.get("section_9a_equity_total_amount")),
        preference_shares_count=_int_or_none(args.get("section_9a_preference_shares_count")),
        preference_nominal_per_share=_dec(args.get("section_9a_preference_nominal_per_share")),
        preference_total_amount=_dec(args.get("section_9a_preference_total_amount")),
        unclassified_shares_count=_int_or_none(args.get("section_9a_unclassified_shares_count")),
        unclassified_total_amount=_dec(args.get("section_9a_unclassified_total_amount")),
    )

    section_9a_total = _dec_required(
        args.get("section_9a_total_amount"), "section_9a_total_amount", parse_errors
    )

    authorised_capital = AuthorisedCapitalBlock(
        total_amount=section_9a_total,
        breakdown=breakdown,
    )

    existing_cap = _dec_required(args.get("existing_authorised_capital"), "existing_authorised_capital", parse_errors)
    revised_cap = _dec_required(args.get("revised_authorised_capital"), "revised_authorised_capital", parse_errors)
    addition = _dec(args.get("difference_addition"))

    if existing_cap is not None and revised_cap is not None and addition is not None:
        if existing_cap + addition != revised_cap:
            parse_errors.append(
                f"Arithmetic mismatch: existing({existing_cap}) + addition({addition}) != revised({revised_cap})"
            )

    return SH7Extraction(
        # Source
        source_filename=filename,
        # Identity
        cin=args.get("cin") or "",
        company_name=args.get("company_name") or "",
        registered_address=args.get("registered_address") or "",
        email=args.get("email") or "",
        # Event
        purpose=args.get("purpose") or "",
        meeting_date=_parse_date_required(args.get("meeting_date"), "meeting_date", parse_errors),
        resolution_type=args.get("resolution_type") or "Ordinary",
        # Capital
        existing_authorised_capital=existing_cap or Decimal("0"),
        revised_authorised_capital=revised_cap or Decimal("0"),
        difference_addition=addition,
        authorised_capital=authorised_capital,
        # Footer
        srn=args.get("srn") or None,
        filing_date=_parse_date(args.get("filing_date")),
        # Stamp duty
        stamp_duty_state=args.get("stamp_duty_state") or None,
        stamp_duty_amount=_dec(args.get("stamp_duty_amount")),
        # Attachments
        attachment_filenames_raw=list(args.get("attachment_filenames_raw") or []),
        # Quality
        extraction_confidence=float(args.get("extraction_confidence", 0.5)),
        unconfirmed_fields=unconfirmed,
        extraction_errors=parse_errors,
    )

# ---------------------------------------------------------------------------
# Node entry-point
# ---------------------------------------------------------------------------

def run_sh7_extractor(state: PipelineState) -> PipelineState:
    """
    SH-7 Extractor node entry-point called by the LangGraph runner.

    For each DocumentGroup in state["document_groups"], runs a single Gemini
    function-calling extraction on the SH-7 content (group.sh7 field only).

    Args:
        state: Mutable pipeline state dict.

    Returns:
        Updated state with:
          - extracted_sh7s           list[SH7Extraction]
          - sh7_extraction_errors    list[dict]
          - completed_stages         extended with "sh7_extractor"

    Raises:
        ValueError: If every SH-7 fails extraction (zero successes).
    """
    document_groups: list[DocumentGroup] = state.get("document_groups") or []
    pipeline_errors: list[dict] = list(state.get("pipeline_errors") or [])
    sh7_extraction_errors: list[dict] = list(state.get("sh7_extraction_errors") or [])

    logger.info("SH-7 Extractor started | groups=%d", len(document_groups))

    extracted_sh7s: list[SH7Extraction] = []

    for group in document_groups:
        sh7_doc = group.sh7
        filename = sh7_doc.file_metadata.filename
        content = sh7_doc.file_metadata.raw_content

        logger.info("Extracting SH-7: %s", filename)

        try:
            args = _call_llm(content)
            if args is None:
                raise RuntimeError("LLM returned no function call")

            extraction = build_extraction(filename, args)
            extracted_sh7s.append(extraction)

            logger.info(
                "SH-7 extracted | file=%s cin=%s meeting=%s existing=%s revised=%s "
                "confidence=%.2f validation_errors=%d",
                filename,
                extraction.cin,
                extraction.meeting_date,
                extraction.existing_authorised_capital,
                extraction.revised_authorised_capital,
                extraction.extraction_confidence,
                len(extraction.extraction_errors),
            )

        except Exception as exc:  # noqa: BLE001
            err_entry = {"filename": filename, "error_message": str(exc)}
            sh7_extraction_errors.append(err_entry)
            pipeline_errors.append({
                "filename": filename,
                "error": str(exc),
                "stage": "sh7_extractor",
            })
            logger.error("SH-7 extraction failed for %s: %s", filename, exc)

    # Terminate if nothing succeeded
    if not extracted_sh7s:
        raise ValueError(
            f"SH-7 Extractor: all {len(document_groups)} extractions failed. "
            "Cannot proceed. Check sh7_extraction_errors for details."
        )

    logger.info(
        "SH-7 Extractor complete | success=%d failures=%d",
        len(extracted_sh7s), len(sh7_extraction_errors),
    )

    completed = list(state.get("completed_stages") or [])
    completed.append("sh7_extractor")

    state["extracted_sh7s"] = extracted_sh7s
    state["sh7_extraction_errors"] = sh7_extraction_errors
    state["pipeline_errors"] = pipeline_errors
    state["completed_stages"] = completed
    return state
