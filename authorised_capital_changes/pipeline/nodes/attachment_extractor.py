"""
Node 4 — Attachment Extractor (attachment_extractor.py)
========================================================
Uses Gemini function-calling to extract structured data from each attachment
that is present inside a DocumentGroup.

One LLM call per present attachment type:
  • board_resolution  → BoardResolutionExtraction
  • egm_resolution    → EGMResolutionExtraction
  • moa               → MOAExtraction

If an attachment is None on the group, no call is made.
All LLM errors are caught per-extraction; the rest of the group continues.

Output: state["attachment_bundles"]  (list[AttachmentExtractionBundle])
"""

from __future__ import annotations

import logging
import os
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from google.genai import types

from authorised_capital_changes.schemas.attachment import (
    BoardResolutionExtraction,
    EGMResolutionExtraction,
    MOAExtraction,
)
from authorised_capital_changes.schemas.document import (
    ClassifiedDocument,
    DocumentGroup,
)
from authorised_capital_changes.schemas.pipeline_state import (
    AttachmentExtractionBundle,
    PipelineState,
)
from authorised_capital_changes.services.llm_client import default_llm_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GEMINI_MODEL: str = os.getenv("EXTRACTOR_GEMINI_MODEL", "gemini-2.5-flash")

# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

_BOARD_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="extract_board_resolution",
            description="Extract structured fields from an Indian MCA Board Resolution.",
            parameters={
                "type": "OBJECT",
                "properties": {
                    "meeting_date": {
                        "type": "STRING",
                        "description": "Date of the board meeting in DD/MM/YYYY or YYYY-MM-DD. Null if not found.",
                    },
                    "resolved_capital_amount": {
                        "type": "STRING",
                        "description": (
                            "Authorised capital amount the board resolved to increase TO "
                            "(not from). Plain numeric string in rupees, no commas. "
                            "Null if not explicitly stated."
                        ),
                    },
                    "resolution_type": {
                        "type": "STRING",
                        "enum": ["Ordinary", "Special"],
                        "description": "Ordinary or Special. Null if not found.",
                    },
                    "cin": {
                        "type": "STRING",
                        "description": "Company Identification Number. Null if not found.",
                    },
                    "extraction_confidence": {
                        "type": "NUMBER",
                        "description": "Confidence score in [0,1].",
                    },
                    "unconfirmed_fields": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "Field names that are uncertain.",
                    },
                    "extraction_errors": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "Any errors encountered during extraction.",
                    },
                },
                "required": ["extraction_confidence", "unconfirmed_fields", "extraction_errors"],
            },
        )
    ]
)

_EGM_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="extract_egm_resolution",
            description="Extract structured fields from an Indian MCA EGM/AGM Resolution.",
            parameters={
                "type": "OBJECT",
                "properties": {
                    "meeting_date": {
                        "type": "STRING",
                        "description": "Date of the meeting in DD/MM/YYYY or YYYY-MM-DD. Null if not found.",
                    },
                    "meeting_type": {
                        "type": "STRING",
                        "enum": ["EGM", "AGM"],
                        "description": (
                            "EGM or AGM. ONLY if the literal word appears in the "
                            "document body. Never infer from filename. Null if absent."
                        ),
                    },
                    "resolved_capital_amount": {
                        "type": "STRING",
                        "description": (
                            "Authorised capital amount the members resolved to increase TO. "
                            "Plain numeric string in rupees, no commas. "
                            "Null if not explicitly stated."
                        ),
                    },
                    "cin": {
                        "type": "STRING",
                        "description": "Company Identification Number. Null if not found.",
                    },
                    "extraction_confidence": {
                        "type": "NUMBER",
                        "description": "Confidence score in [0,1].",
                    },
                    "unconfirmed_fields": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "Field names that are uncertain.",
                    },
                    "extraction_errors": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "Any errors encountered during extraction.",
                    },
                },
                "required": ["extraction_confidence", "unconfirmed_fields", "extraction_errors"],
            },
        )
    ]
)

_MOA_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="extract_moa",
            description="Extract Clause V capital fields from an Indian MCA Memorandum of Association.",
            parameters={
                "type": "OBJECT",
                "properties": {
                    "incorporation_capital": {
                        "type": "STRING",
                        "description": (
                            "Total authorised capital in Clause V in rupees. "
                            "Plain numeric string, no commas. Null if not found."
                        ),
                    },
                    "equity_shares_count": {
                        "type": "INTEGER",
                        "description": "Number of equity shares from Clause V. Null if not found.",
                    },
                    "nominal_per_share": {
                        "type": "STRING",
                        "description": (
                            "Nominal value per equity share in rupees. "
                            "Plain numeric string, no commas. Null if not found."
                        ),
                    },
                    "preference_shares_count": {
                        "type": "INTEGER",
                        "description": "Number of preference shares from Clause V. Null if absent.",
                    },
                    "preference_nominal_per_share": {
                        "type": "STRING",
                        "description": (
                            "Nominal value per preference share in rupees. "
                            "Plain numeric string, no commas. Null if absent."
                        ),
                    },
                    "cin": {
                        "type": "STRING",
                        "description": "Company Identification Number. Null if not found.",
                    },
                    "extraction_confidence": {
                        "type": "NUMBER",
                        "description": "Confidence score in [0,1].",
                    },
                    "unconfirmed_fields": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "Field names that are uncertain.",
                    },
                    "extraction_errors": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "Any errors encountered during extraction.",
                    },
                },
                "required": ["extraction_confidence", "unconfirmed_fields", "extraction_errors"],
            },
        )
    ]
)

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

_BOARD_SYSTEM = (
    "You are an expert in Indian corporate law and MCA board resolutions. "
    "Extract ONLY: date of the board meeting, capital amount the board resolved to "
    "increase authorised capital TO (not from), resolution type (Ordinary or Special), "
    "and CIN of the company. "
    "Never infer. If a field is not explicitly stated, set it to null. "
    "Return your answer ONLY via the extract_board_resolution tool call."
)

_EGM_SYSTEM = (
    "You are an expert in Indian corporate law and MCA EGM/AGM resolutions. "
    "Extract ONLY: date of the meeting, meeting type (EGM or AGM — ONLY if the word "
    "literally appears in the document body; never infer from filename), capital amount "
    "the members resolved to increase TO, and CIN of the company. "
    "Never infer. If a field is not explicitly stated, set it to null. "
    "Return your answer ONLY via the extract_egm_resolution tool call."
)

_MOA_SYSTEM = (
    "You are an expert in Indian corporate law and Memoranda of Association. "
    "Extract ONLY from Clause V: total authorised capital amount in rupees, "
    "number of equity shares, nominal value per equity share, number of preference shares "
    "(null if not present), nominal value per preference share (null if not present), "
    "and CIN if present. "
    "Never infer. If not explicitly stated in Clause V, set to null. "
    "Return your answer ONLY via the extract_moa tool call."
)


# ---------------------------------------------------------------------------
# Helper: safe decimal conversion
# ---------------------------------------------------------------------------

def _to_decimal(value: Any) -> Decimal | None:
    """Convert a string or number from LLM output to Decimal, or None on failure."""
    if value is None:
        return None
    try:
        # Remove commas and whitespace that sneak through despite instructions
        cleaned = str(value).replace(",", "").strip()
        if not cleaned or cleaned.lower() == "null":
            return None
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def _to_date(value: Any) -> date | None:
    """Parse DD/MM/YYYY or YYYY-MM-DD strings to date, or None on failure."""
    if not value:
        return None
    s = str(value).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            from datetime import datetime
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _to_int(value: Any) -> int | None:
    """Convert to int safely."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# LLM call helper
# ---------------------------------------------------------------------------

def _call_llm(
    system_prompt: str,
    user_content: str,
    tool: types.Tool,
    tool_name: str,
) -> dict | None:
    """
    Make a single Gemini function-calling request.

    Returns the args dict from the first matching function call,
    or None on any failure.
    """
    return default_llm_client.extract_structured_data(
        system_instruction=system_prompt,
        user_prompt=user_content,
        tool=tool,
        tool_name=tool_name
    )


# ---------------------------------------------------------------------------
# Per-type extraction functions
# ---------------------------------------------------------------------------

def _extract_board_resolution(doc: ClassifiedDocument) -> BoardResolutionExtraction:
    """Run LLM extraction on a Board Resolution document."""
    filename = doc.file_metadata.filename
    content = doc.file_metadata.raw_content

    args = _call_llm(_BOARD_SYSTEM, content, _BOARD_TOOL, "extract_board_resolution")

    if args is None:
        return BoardResolutionExtraction(
            source_filename=filename,
            cin=None,
            meeting_date=None,
            resolved_capital_amount=None,
            resolution_type=None,
            extraction_confidence=0.0,
            unconfirmed_fields=[],
            extraction_errors=["LLM call failed or returned no function call"],
        )

    return BoardResolutionExtraction(
        source_filename=filename,
        cin=args.get("cin") or None,
        meeting_date=_to_date(args.get("meeting_date")),
        resolved_capital_amount=_to_decimal(args.get("resolved_capital_amount")),
        resolution_type=args.get("resolution_type") or None,
        extraction_confidence=float(args.get("extraction_confidence", 0.5)),
        unconfirmed_fields=list(args.get("unconfirmed_fields") or []),
        extraction_errors=list(args.get("extraction_errors") or []),
    )


def _extract_egm_resolution(doc: ClassifiedDocument) -> EGMResolutionExtraction:
    """Run LLM extraction on an EGM/AGM Resolution document."""
    filename = doc.file_metadata.filename
    content = doc.file_metadata.raw_content

    args = _call_llm(_EGM_SYSTEM, content, _EGM_TOOL, "extract_egm_resolution")

    if args is None:
        return EGMResolutionExtraction(
            source_filename=filename,
            cin=None,
            meeting_date=None,
            meeting_type=None,
            resolved_capital_amount=None,
            extraction_confidence=0.0,
            unconfirmed_fields=[],
            extraction_errors=["LLM call failed or returned no function call"],
        )

    return EGMResolutionExtraction(
        source_filename=filename,
        cin=args.get("cin") or None,
        meeting_date=_to_date(args.get("meeting_date")),
        meeting_type=args.get("meeting_type") or None,
        resolved_capital_amount=_to_decimal(args.get("resolved_capital_amount")),
        extraction_confidence=float(args.get("extraction_confidence", 0.5)),
        unconfirmed_fields=list(args.get("unconfirmed_fields") or []),
        extraction_errors=list(args.get("extraction_errors") or []),
    )


def _extract_moa(doc: ClassifiedDocument) -> MOAExtraction:
    """Run LLM extraction on a Memorandum of Association document."""
    filename = doc.file_metadata.filename
    content = doc.file_metadata.raw_content

    args = _call_llm(_MOA_SYSTEM, content, _MOA_TOOL, "extract_moa")

    if args is None:
        return MOAExtraction(
            source_filename=filename,
            cin=None,
            incorporation_capital=None,
            equity_shares_count=None,
            nominal_per_share=None,
            preference_shares_count=None,
            preference_nominal_per_share=None,
            extraction_confidence=0.0,
            unconfirmed_fields=[],
            extraction_errors=["LLM call failed or returned no function call"],
        )

    return MOAExtraction(
        source_filename=filename,
        cin=args.get("cin") or None,
        incorporation_capital=_to_decimal(args.get("incorporation_capital")),
        equity_shares_count=_to_int(args.get("equity_shares_count")),
        nominal_per_share=_to_decimal(args.get("nominal_per_share")),
        preference_shares_count=_to_int(args.get("preference_shares_count")),
        preference_nominal_per_share=_to_decimal(args.get("preference_nominal_per_share")),
        extraction_confidence=float(args.get("extraction_confidence", 0.5)),
        unconfirmed_fields=list(args.get("unconfirmed_fields") or []),
        extraction_errors=list(args.get("extraction_errors") or []),
    )


# ---------------------------------------------------------------------------
# Core: process one DocumentGroup
# ---------------------------------------------------------------------------

def _process_group(
    group: DocumentGroup,
    pipeline_errors: list[dict],
) -> AttachmentExtractionBundle:
    """
    Extract from all present attachments in a single DocumentGroup.

    Each attachment type runs independently; errors are caught per-extraction
    so one failure cannot block others.
    """
    sh7_filename = group.sh7.file_metadata.filename

    board_extraction: BoardResolutionExtraction | None = None
    egm_extraction: EGMResolutionExtraction | None = None
    moa_extraction: MOAExtraction | None = None

    # Board Resolution
    if group.board_resolution is not None:
        try:
            board_extraction = _extract_board_resolution(group.board_resolution)
            logger.info(
                "Board extraction done | sh7=%s confidence=%.2f",
                sh7_filename, board_extraction.extraction_confidence,
            )
        except Exception as exc:  # noqa: BLE001
            pipeline_errors.append({
                "filename": group.board_resolution.file_metadata.filename,
                "error": str(exc),
                "stage": "attachment_extractor_board",
            })
            logger.error("Board extraction crashed for %s: %s", sh7_filename, exc)

    # EGM Resolution
    if group.egm_resolution is not None:
        try:
            egm_extraction = _extract_egm_resolution(group.egm_resolution)
            logger.info(
                "EGM extraction done | sh7=%s confidence=%.2f",
                sh7_filename, egm_extraction.extraction_confidence,
            )
        except Exception as exc:  # noqa: BLE001
            pipeline_errors.append({
                "filename": group.egm_resolution.file_metadata.filename,
                "error": str(exc),
                "stage": "attachment_extractor_egm",
            })
            logger.error("EGM extraction crashed for %s: %s", sh7_filename, exc)

    # MOA
    if group.moa is not None:
        try:
            moa_extraction = _extract_moa(group.moa)
            logger.info(
                "MOA extraction done | sh7=%s confidence=%.2f",
                sh7_filename, moa_extraction.extraction_confidence,
            )
        except Exception as exc:  # noqa: BLE001
            pipeline_errors.append({
                "filename": group.moa.file_metadata.filename,
                "error": str(exc),
                "stage": "attachment_extractor_moa",
            })
            logger.error("MOA extraction crashed for %s: %s", sh7_filename, exc)

    return AttachmentExtractionBundle(
        event_index=group.event_index,
        sh7_filename=sh7_filename,
        board_resolution=board_extraction,
        egm_resolution=egm_extraction,
        moa=moa_extraction,
    )


# ---------------------------------------------------------------------------
# Node entry-point
# ---------------------------------------------------------------------------

def run_attachment_extractor(state: PipelineState) -> PipelineState:
    """
    Attachment Extractor node entry-point called by the LangGraph runner.

    Iterates every DocumentGroup in state["document_groups"] and runs one
    Gemini function-calling extraction per present attachment (board/EGM/MOA).
    Groups with no attachments get a bundle with all-None extractions.

    Args:
        state: Mutable pipeline state dict.

    Returns:
        Updated state with:
          - attachment_bundles   list[AttachmentExtractionBundle]
          - completed_stages     extended with "attachment_extractor"
    """
    document_groups: list[DocumentGroup] = state.get("document_groups") or []
    pipeline_errors: list[dict] = list(state.get("pipeline_errors") or [])

    logger.info(
        "Attachment Extractor started | group_count=%d", len(document_groups)
    )

    bundles: list[AttachmentExtractionBundle] = []

    for group in document_groups:
        sh7_filename = group.sh7.file_metadata.filename
        try:
            bundle = _process_group(group, pipeline_errors)
            bundles.append(bundle)
        except Exception as exc:  # noqa: BLE001
            pipeline_errors.append({
                "filename": sh7_filename,
                "error": str(exc),
                "stage": "attachment_extractor",
            })
            logger.error(
                "Group processing crashed entirely for %s: %s", sh7_filename, exc
            )

    logger.info(
        "Attachment Extractor complete | bundles=%d pipeline_errors=%d",
        len(bundles), len(pipeline_errors),
    )

    completed = list(state.get("completed_stages") or [])
    completed.append("attachment_extractor")

    state["attachment_bundles"] = bundles
    state["pipeline_errors"] = pipeline_errors
    state["completed_stages"] = completed
    return state
