"""
Node 2 — Classifier
===================
Two-pass classification for every FileMetadata in state["raw_files"].

Pass 1 — Rule-based (no LLM):
  Priority 1  Filename keywords   → confidence 0.92
  Priority 2  Content keywords    → confidence 0.87
  Priority 3  Official status     → independent of type (SRN / CTC / DRAFT)

Pass 2 — LLM fallback (Gemini function-calling):
  Triggered when rule-based confidence < 0.85.
  Uses the first 500 tokens (~2000 chars) of document content.
  Returns JSON via tool_use: {document_type, official_status, confidence, reason}.

Routing after classification:
  confidence < 0.60            → unclassified_documents (flagged, not guessed)
  document_type == SH7         → sh7_documents
  all others                   → non_sh7_documents

Duplicate SH-7 pre-check:
  Two SH-7s sharing the same event_date_hint → logged as pipeline errors.
  Pipeline terminates with ValueError if sh7_documents is empty after dedup.

Output keys:
  classified_docs, sh7_documents, non_sh7_documents, unclassified_documents
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections import defaultdict
from datetime import date, datetime
from typing import Optional

from google.genai import types

from authorised_capital_changes.schemas.document import (
    ClassifiedDocument,
    DocumentType,
    FileMetadata,
    OfficialStatus,
)
from authorised_capital_changes.schemas.pipeline_state import PipelineState
from authorised_capital_changes.services.llm_client import default_llm_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CONFIDENCE_FILENAME: float = 0.92
_CONFIDENCE_CONTENT: float = 0.87
_LLM_FALLBACK_THRESHOLD: float = 0.85   # trigger LLM when below this
_HUMAN_REVIEW_THRESHOLD: float = 0.60   # route to unclassified when below this

# SRN pattern: H followed by exactly 8 digits (e.g. H45678902)
_SRN_PATTERN: re.Pattern = re.compile(r"\bH\d{8}\b")

# Date patterns commonly found in Indian MCA filings  DD/MM/YYYY  or  YYYY-MM-DD
_DATE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b"),   # DD/MM/YYYY
    re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"),   # YYYY-MM-DD
]

# CIN pattern
_CIN_PATTERN: re.Pattern = re.compile(
    r"\b[UL]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b"
)

# LLM model identifier (uses environment variable with sensible default)
_GEMINI_MODEL: str = os.getenv("CLASSIFIER_GEMINI_MODEL", "gemini-2.5-flash")

# Characters used as the "500 token" content window for the LLM
_LLM_CONTENT_CHARS: int = 2000


# ---------------------------------------------------------------------------
# Helper: official status detection
# ---------------------------------------------------------------------------

def _detect_official_status(filename: str, content: str) -> OfficialStatus:
    """Determine official status independent of document type.

    Priority order:
      1. SRN H\\d{8} present → OFFICIAL
      2. "CERTIFIED TRUE COPY" present → CERTIFIED_COPY
      3. Neither → DRAFT
    """
    combined = filename + " " + content
    if _SRN_PATTERN.search(combined):
        return OfficialStatus.OFFICIAL
    if "CERTIFIED TRUE COPY" in content.upper():
        return OfficialStatus.CERTIFIED_COPY
    return OfficialStatus.DRAFT


# ---------------------------------------------------------------------------
# Helper: date extraction for event_date_hint
# ---------------------------------------------------------------------------

def _extract_event_date(content: str) -> Optional[date]:
    """Return the first parseable date found in the document content."""
    for pattern in _DATE_PATTERNS:
        match = pattern.search(content)
        if match:
            try:
                groups = match.groups()
                if len(groups[0]) == 4:          # YYYY-MM-DD
                    return date(int(groups[0]), int(groups[1]), int(groups[2]))
                else:                             # DD/MM/YYYY
                    return date(int(groups[2]), int(groups[1]), int(groups[0]))
            except ValueError:
                continue
    return None


# ---------------------------------------------------------------------------
# Helper: CIN extraction
# ---------------------------------------------------------------------------

def _extract_cin(content: str) -> Optional[str]:
    """Return the first CIN found in the document content, or None."""
    match = _CIN_PATTERN.search(content)
    return match.group(0) if match else None


# ---------------------------------------------------------------------------
# Pass 1: filename-based classification
# ---------------------------------------------------------------------------

def _classify_by_filename(filename: str) -> Optional[DocumentType]:
    """
    Apply filename keyword rules (Priority 1).

    EGM_NOTICE must be checked before EGM_RESOLUTION because the EGM+Notice
    rule is the more specific case.

    Returns DocumentType or None if no rule matches.
    """
    name_upper = filename.upper()

    if "SH7" in name_upper or "SH-7" in name_upper:
        return DocumentType.SH7
    if "BOARDMEETING" in name_upper:
        return DocumentType.BOARD_MEETING_RESOLUTION
    if "EGM" in name_upper and "NOTICE" in name_upper:
        return DocumentType.EGM_NOTICE
    if "EGM" in name_upper:
        return DocumentType.EGM_RESOLUTION
    if "MOA" in name_upper:
        return DocumentType.MOA
    if "PAS3" in name_upper or "PAS-3" in name_upper:
        return DocumentType.PAS3
    if "ALLOTTEES" in name_upper:
        return DocumentType.LIST_OF_ALLOTTEES
    return None


# ---------------------------------------------------------------------------
# Pass 1: content-based classification
# ---------------------------------------------------------------------------

def _classify_by_content(content: str) -> Optional[DocumentType]:
    """
    Apply content keyword rules (Priority 2).

    Returns DocumentType or None if no rule matches.
    """
    upper = content.upper()

    if "FORM NO. SH-7" in upper:
        return DocumentType.SH7
    if "NOTICE TO REGISTRAR" in upper and "ALTERATION OF SHARE CAPITAL" in upper:
        return DocumentType.SH7
    if "FORM NO. PAS-3" in upper:
        return DocumentType.PAS3
    if "RETURN OF ALLOTMENT" in upper:
        return DocumentType.PAS3
    if "CERTIFIED TRUE COPY" in upper and "BOARD OF DIRECTORS" in upper:
        return DocumentType.BOARD_MEETING_RESOLUTION
    if "EXTRA ORDINARY GENERAL" in upper:
        return DocumentType.EGM_RESOLUTION
    if "MEMORANDUM OF ASSOCIATION" in upper and "CLAUSE V" in upper:
        return DocumentType.MOA
    return None


# ---------------------------------------------------------------------------
# Pass 2: LLM fallback via Gemini function-calling
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field

class ClassificationResult(BaseModel):
    document_type: str = Field(description="Exact document type. Must be one of: SH7, PAS3, BOARD_MEETING_RESOLUTION, EGM_RESOLUTION, EGM_NOTICE, MOA, LIST_OF_ALLOTTEES, UNKNOWN.")
    official_status: str = Field(description="Official status of the document. Must be one of: OFFICIAL, CERTIFIED_COPY, DRAFT, UNCONFIRMED.")
    confidence: float = Field(description="Classification confidence in [0, 1].")
    reason: str = Field(description="One-sentence rationale.")

_SYSTEM_PROMPT = (
    "You are a document classifier for Indian MCA corporate filings. "
    "Classify the provided document excerpt into exactly one type: "
    "SH7, PAS3, BOARD_MEETING_RESOLUTION, EGM_RESOLUTION, EGM_NOTICE, "
    "MOA, LIST_OF_ALLOTTEES, UNKNOWN. "
    "Determine its official status: OFFICIAL, CERTIFIED_COPY, DRAFT, UNCONFIRMED. "
)

def _llm_classify(file_meta: FileMetadata) -> tuple[DocumentType, OfficialStatus, float, str]:
    """
    Call LLM with structured output to classify a document.
    """
    content_window = file_meta.raw_content[:_LLM_CONTENT_CHARS]
    user_message = (
        f"Filename: {file_meta.filename}\n\n"
        f"Document excerpt:\n{content_window}"
    )

    try:
        args = default_llm_client.extract_structured_data(
            system_instruction=_SYSTEM_PROMPT,
            user_prompt=user_message,
            response_model=ClassificationResult
        )
        
        if args is not None:
            doc_type = DocumentType(args.get("document_type", "UNKNOWN"))
            status = OfficialStatus(args.get("official_status", "UNCONFIRMED"))
            confidence = float(args.get("confidence", 0.5))
            logger.debug(
                "LLM classified %s → %s (%.2f)",
                file_meta.filename, doc_type, confidence,
            )
            return doc_type, status, confidence, "llm_fallback"
            
        logger.warning("LLM returned no valid args for %s", file_meta.filename)
        return DocumentType.UNKNOWN, OfficialStatus.UNCONFIRMED, 0.0, "llm_error"
        
    except Exception as exc:  # noqa: BLE001
        logger.error("LLM classification failed for %s: %s", file_meta.filename, exc)
        return DocumentType.UNKNOWN, OfficialStatus.UNCONFIRMED, 0.0, "llm_error"


# ---------------------------------------------------------------------------
# Core: classify a single FileMetadata
# ---------------------------------------------------------------------------

def _classify_one(file_meta: FileMetadata) -> ClassifiedDocument:
    """
    Classify a single file through Pass 1 → Pass 2 → routing.

    Returns a fully populated ClassifiedDocument.
    """
    filename = file_meta.filename
    content = file_meta.raw_content

    # --- Pass 1a: filename ---------------------------------------------------
    doc_type = _classify_by_filename(filename)
    if doc_type is not None:
        confidence = _CONFIDENCE_FILENAME
        method = "rule_based"
    else:
        # --- Pass 1b: content ------------------------------------------------
        doc_type = _classify_by_content(content)
        if doc_type is not None:
            confidence = _CONFIDENCE_CONTENT
            method = "rule_based"
        else:
            doc_type = DocumentType.UNKNOWN
            confidence = 0.0
            method = "rule_based"

    # --- Pass 1c: official status (independent) ------------------------------
    official_status = _detect_official_status(filename, content)

    # --- Pass 2: LLM fallback ------------------------------------------------
    if confidence < _LLM_FALLBACK_THRESHOLD:
        llm_type, llm_status, llm_confidence, llm_method = _llm_classify(file_meta)
        # Accept LLM result only when it improves confidence
        if llm_confidence > confidence:
            doc_type = llm_type
            official_status = llm_status
            confidence = llm_confidence
            method = llm_method

    # --- Ancillary fields ----------------------------------------------------
    event_date_hint = _extract_event_date(content)
    cin_hint = _extract_cin(content)

    requires_human_review = confidence < _HUMAN_REVIEW_THRESHOLD
    review_reason = "LOW_CONFIDENCE" if requires_human_review else None

    return ClassifiedDocument(
        file_metadata=file_meta,
        document_type=doc_type,
        official_status=official_status,
        classification_method=method,
        classification_confidence=confidence,
        event_date_hint=event_date_hint,
        cin_hint=cin_hint,
        requires_human_review=requires_human_review,
        review_reason=review_reason,
    )


# ---------------------------------------------------------------------------
# Duplicate SH-7 pre-check
# ---------------------------------------------------------------------------

def _deduplicate_sh7s(
    sh7_docs: list[ClassifiedDocument],
    pipeline_errors: list[dict],
) -> list[ClassifiedDocument]:
    """
    Detect SH-7s that share the same event_date_hint.

    Duplicates are logged as pipeline errors and removed from sh7_documents.
    Returns the cleaned sh7_documents list.
    """
    # Group by event_date_hint (None-keyed entries are kept; they cannot clash)
    date_groups: dict[date | None, list[ClassifiedDocument]] = defaultdict(list)
    for doc in sh7_docs:
        date_groups[doc.event_date_hint].append(doc)

    clean_sh7s: list[ClassifiedDocument] = []

    for event_date, group in date_groups.items():
        if event_date is None or len(group) == 1:
            clean_sh7s.extend(group)
            continue

        # Duplicate detected — log and drop
        filenames = [d.file_metadata.filename for d in group]
        logger.warning(
            "Duplicate SH-7 event_date_hint=%s across files: %s",
            event_date, filenames,
        )
        pipeline_errors.append({
            "filename": str(filenames),
            "error": (
                f"Duplicate SH-7 meeting date {event_date} found in: {filenames}"
            ),
            "stage": "classifier_dedup",
        })

    return clean_sh7s


# ---------------------------------------------------------------------------
# Node entry-point
# ---------------------------------------------------------------------------

def run_classifier(state: PipelineState) -> PipelineState:
    """
    Classifier node entry-point called by the LangGraph runner.

    Reads state["raw_files"], classifies each file, routes results into
    sh7_documents / non_sh7_documents / unclassified_documents, performs
    duplicate SH-7 deduplication, then raises ValueError if no valid SH-7s
    remain (pipeline cannot continue without at least one SH-7).

    Args:
        state: Mutable pipeline state dict.

    Returns:
        Updated state with classified_docs, sh7_documents, non_sh7_documents,
        unclassified_documents, and completed_stages extended with "classifier".

    Raises:
        ValueError: If sh7_documents is empty after deduplication.
    """
    raw_files: list[FileMetadata] = state.get("raw_files") or []
    pipeline_errors: list[dict] = list(state.get("pipeline_errors") or [])

    logger.info("Classifier started | file_count=%d", len(raw_files))

    classified_docs: list[ClassifiedDocument] = []
    sh7_documents: list[ClassifiedDocument] = []
    non_sh7_documents: list[ClassifiedDocument] = []
    unclassified_documents: list[ClassifiedDocument] = []

    for file_meta in raw_files:
        try:
            doc = _classify_one(file_meta)
        except Exception as exc:  # noqa: BLE001
            pipeline_errors.append({
                "filename": file_meta.filename,
                "error": str(exc),
                "stage": "classifier",
            })
            logger.error("Classification crashed for %s: %s", file_meta.filename, exc)
            continue

        classified_docs.append(doc)

        # Route by confidence first, then by type
        if doc.classification_confidence < _HUMAN_REVIEW_THRESHOLD:
            unclassified_documents.append(doc)
            logger.info(
                "Low-confidence → flagged as unclassified: %s (%.2f)",
                file_meta.filename, doc.classification_confidence,
            )
        elif doc.document_type == DocumentType.SH7:
            sh7_documents.append(doc)
        else:
            non_sh7_documents.append(doc)

    # --- Duplicate SH-7 pre-check -------------------------------------------
    sh7_documents = _deduplicate_sh7s(
        sh7_documents, pipeline_errors
    )

    logger.info(
        "Classifier complete | classified=%d sh7=%d non_sh7=%d "
        "unclassified=%d",
        len(classified_docs),
        len(sh7_documents),
        len(non_sh7_documents),
        len(unclassified_documents),
    )

    # --- Terminate if no SH-7s remain ----------------------------------------
    if not sh7_documents:
        msg = (
            "No valid SH-7 documents remain after classification and deduplication. "
            "Pipeline cannot continue."
        )
        pipeline_errors.append({
            "filename": "N/A",
            "error": msg,
            "stage": "classifier_dedup",
        })
        logger.critical(msg)
        raise ValueError(msg)

    # --- Extend completed_stages --------------------------------------------
    completed = list(state.get("completed_stages") or [])
    completed.append("classifier")

    state["classified_docs"] = classified_docs
    state["sh7_documents"] = sh7_documents
    state["non_sh7_documents"] = non_sh7_documents
    state["unclassified_documents"] = unclassified_documents
    state["pipeline_errors"] = pipeline_errors
    state["completed_stages"] = completed
    return state
