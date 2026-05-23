"""
Node 3 — Relationship Resolver
===============================
No LLM. Pure structural parsing + dict-lookup.

For each SH-7 in state["sh7_documents"]:

  Step 1  Parse Field 12 / Attachments section of the raw SH-7 content.
          Extract every filename string exactly as written.

  Step 2  Match each extracted filename against state["non_sh7_documents"]:
            Primary   — exact case-insensitive filename match
            Secondary — strip extension, compare stems (case-insensitive)
          Unmatched refs → unmatched_attachment_refs[sh7_filename]

  Step 3  Assign matched documents to the DocumentGroup by type:
            BOARD_MEETING_RESOLUTION → group.board_resolution
            EGM_RESOLUTION           → group.egm_resolution
            MOA                      → group.moa
          Any other matched type is logged and silently skipped.

  Step 4  NO independent MOA search — MOA is linked ONLY if listed in Field 12.

  Step 5  Derive event_index from the SH-7 filename pattern
          "Event<N>" or "_<N>_" (e.g. SH7_Event2_2019.md → 2).
          Defaults to 0 if no numeric event indicator found; Assembler sorts later.

Output: state["document_groups"], state["unmatched_attachment_refs"]
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from authorised_capital_changes.schemas.document import (
    ClassifiedDocument,
    DocumentGroup,
    DocumentType,
)
from authorised_capital_changes.schemas.pipeline_state import PipelineState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Noise strings found in the Attachments table that are NOT real filenames.
# Checked case-insensitively; any cell whose stripped text contains one of
# these substrings is discarded.
_ATTACHMENT_NOISE: tuple[str, ...] = (
    "list of attachments",
    "copy of the resolution",
    "altered memorandum of association",
    "optional attachments",
    "remove attachment",
    "attach",                   # standalone "Attach" button label
    "copy of the",
    "(1)",
    "(2)",
    "(3)",
    "(4)",
    "(5)",
    "(6)",
    "(7)",
    "(8)",
    "(9)",
)

# Regex: extract an event number from filenames like
#   SH7_Event2_2019.md, BoardMeeting_Event4_2024.md, MOA_Event1_2018.md
_EVENT_INDEX_RE = re.compile(r"[Ee]vent(\d+)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Step 1 — Attachment filename parser
# ---------------------------------------------------------------------------

def _parse_attachment_filenames(raw_content: str) -> list[str]:
    """
    Extract attachment filenames from the Attachments section of an SH-7.

    The section is demarcated by the `## Attachments` heading.  Filenames are
    cell values inside an HTML ``<table>`` that:
      - contain a file extension (any non-whitespace chars after a dot)
      - are not pure noise / boilerplate labels

    Returns a list of raw filename strings exactly as they appear in the source.
    """
    # Locate the Attachments section — everything after "## Attachments"
    # but before the next "## " heading (usually "## Declaration")
    section_match = re.search(
        r"##\s+Attachments\b(.*?)(?=##\s+|$)",
        raw_content,
        re.IGNORECASE | re.DOTALL,
    )
    if not section_match:
        logger.debug("No '## Attachments' section found in content")
        return []

    section_text = section_match.group(1)

    # Pull all <td>...</td> cell values (handles multi-line cells too)
    td_values = re.findall(
        r"<td[^>]*>(.*?)</td>",
        section_text,
        re.IGNORECASE | re.DOTALL,
    )

    filenames: list[str] = []
    for raw_cell in td_values:
        # Strip HTML tags and whitespace
        cell = re.sub(r"<[^>]+>", "", raw_cell).strip()

        if not cell:
            continue

        # Must contain a dot followed by a non-whitespace extension
        if not re.search(r"\.\S+", cell):
            continue

        # Reject boilerplate noise
        cell_lower = cell.lower()
        if any(noise in cell_lower for noise in _ATTACHMENT_NOISE):
            continue

        filenames.append(cell)
        logger.debug("Extracted attachment ref: %r", cell)

    return filenames


# ---------------------------------------------------------------------------
# Step 2 — Filename matcher
# ---------------------------------------------------------------------------

def _build_lookup(
    non_sh7_docs: list[ClassifiedDocument],
) -> tuple[dict[str, ClassifiedDocument], dict[str, ClassifiedDocument]]:
    """
    Build two lookup dicts from non_sh7_documents for fast matching.

    Returns:
        exact_map  — keyed by lowercase filename (with extension)
        stem_map   — keyed by lowercase filename stem (without extension)
    """
    exact_map: dict[str, ClassifiedDocument] = {}
    stem_map: dict[str, ClassifiedDocument] = {}

    for doc in non_sh7_docs:
        fname = doc.file_metadata.filename
        exact_map[fname.lower()] = doc
        stem = Path(fname).stem.lower()
        stem_map[stem] = doc

    return exact_map, stem_map


def _match_filename(
    ref: str,
    exact_map: dict[str, ClassifiedDocument],
    stem_map: dict[str, ClassifiedDocument],
) -> Optional[ClassifiedDocument]:
    """
    Attempt to resolve a raw attachment reference to a ClassifiedDocument.

    Priority:
      1. Exact case-insensitive filename match (including extension)
      2. Stem match (both sides stripped of extension, case-insensitive)

    Returns the matched ClassifiedDocument, or None.
    """
    # Primary — exact filename
    exact_key = ref.strip().lower()
    if exact_key in exact_map:
        return exact_map[exact_key]

    # Secondary — stem (strip extension from the reference too)
    stem_key = Path(ref.strip()).stem.lower()
    if stem_key in stem_map:
        return stem_map[stem_key]

    return None


# ---------------------------------------------------------------------------
# Step 5 — Event index extraction
# ---------------------------------------------------------------------------

def _extract_event_index(sh7_filename: str) -> int:
    """
    Derive a 1-based event index from the SH-7 filename.

    Matches patterns like Event1, Event2, _1_, _2_ etc.
    Returns 0 if no numeric event indicator is found (Assembler will sort).
    """
    m = _EVENT_INDEX_RE.search(sh7_filename)
    if m:
        return int(m.group(1))

    # Fallback: look for a bare digit between underscores
    bare = re.search(r"_(\d+)_", sh7_filename)
    if bare:
        return int(bare.group(1))

    return 0


# ---------------------------------------------------------------------------
# Core: resolve one SH-7
# ---------------------------------------------------------------------------

def _resolve_one_sh7(
    sh7_doc: ClassifiedDocument,
    exact_map: dict[str, ClassifiedDocument],
    stem_map: dict[str, ClassifiedDocument],
) -> tuple[DocumentGroup, list[str]]:
    """
    Build a DocumentGroup for a single SH-7.

    Returns (DocumentGroup, list_of_unmatched_refs).
    """
    sh7_filename = sh7_doc.file_metadata.filename
    raw_content = sh7_doc.file_metadata.raw_content

    # Step 1 — parse attachment refs
    attachment_refs: list[str] = _parse_attachment_filenames(raw_content)
    logger.info(
        "SH-7 %s | attachment_refs_found=%d: %s",
        sh7_filename, len(attachment_refs), attachment_refs,
    )

    board_resolution: Optional[ClassifiedDocument] = None
    egm_resolution: Optional[ClassifiedDocument] = None
    moa: Optional[ClassifiedDocument] = None
    unmatched: list[str] = []

    for ref in attachment_refs:
        # Step 2 — attempt match
        matched_doc = _match_filename(ref, exact_map, stem_map)

        if matched_doc is None:
            unmatched.append(ref)
            logger.info("Unmatched attachment ref in %s: %r", sh7_filename, ref)
            continue

        matched_name = matched_doc.file_metadata.filename
        doc_type = matched_doc.document_type

        # Step 3 — assign by type (strict)
        if doc_type == DocumentType.BOARD_MEETING_RESOLUTION:
            if board_resolution is None:
                board_resolution = matched_doc
                logger.debug("Linked board_resolution: %s → %s", ref, matched_name)
            else:
                logger.warning(
                    "Duplicate BOARD_MEETING_RESOLUTION for SH-7 %s "
                    "(keeping first; skipping %s)",
                    sh7_filename, matched_name,
                )

        elif doc_type == DocumentType.EGM_RESOLUTION:
            if egm_resolution is None:
                egm_resolution = matched_doc
                logger.debug("Linked egm_resolution: %s → %s", ref, matched_name)
            else:
                logger.warning(
                    "Duplicate EGM_RESOLUTION for SH-7 %s "
                    "(keeping first; skipping %s)",
                    sh7_filename, matched_name,
                )

        elif doc_type == DocumentType.MOA:
            # Step 4 — MOA linked only if explicitly in Field 12 (we're already
            # inside an attachment-ref loop, so this is always satisfied here).
            if moa is None:
                moa = matched_doc
                logger.debug("Linked moa: %s → %s", ref, matched_name)
            else:
                logger.warning(
                    "Duplicate MOA for SH-7 %s "
                    "(keeping first; skipping %s)",
                    sh7_filename, matched_name,
                )

        else:
            # Other matched types (EGM_NOTICE, PAS3, etc.) — log and skip
            logger.info(
                "Matched attachment %r → %s (type=%s) for SH-7 %s: "
                "type not used in DocumentGroup; skipping.",
                ref, matched_name, doc_type, sh7_filename,
            )

    # Step 5 — event_index
    event_index = _extract_event_index(sh7_filename)

    group = DocumentGroup(
        event_index=event_index,
        sh7=sh7_doc,
        board_resolution=board_resolution,
        egm_resolution=egm_resolution,
        moa=moa,
        unmatched_attachment_refs=unmatched,
    )

    logger.info(
        "DocumentGroup built | sh7=%s event_index=%d "
        "board=%s egm=%s moa=%s unmatched=%d",
        sh7_filename,
        event_index,
        board_resolution.file_metadata.filename if board_resolution else "None",
        egm_resolution.file_metadata.filename if egm_resolution else "None",
        moa.file_metadata.filename if moa else "None",
        len(unmatched),
    )

    return group, unmatched


# ---------------------------------------------------------------------------
# Node entry-point
# ---------------------------------------------------------------------------

def run_relationship_resolver(state: PipelineState) -> PipelineState:
    """
    Relationship Resolver node entry-point called by the LangGraph runner.

    Iterates sh7_documents, parses each SH-7's Field 12 / Attachments section,
    matches referenced filenames against non_sh7_documents, and constructs
    one DocumentGroup per SH-7.

    Args:
        state: Mutable pipeline state dict.

    Returns:
        Updated state with:
          - document_groups          list[DocumentGroup]
          - unmatched_attachment_refs dict[str, list[str]]
          - completed_stages         extended with "relationship_resolver"
    """
    sh7_documents: list[ClassifiedDocument] = state.get("sh7_documents") or []
    non_sh7_documents: list[ClassifiedDocument] = state.get("non_sh7_documents") or []

    logger.info(
        "Relationship Resolver started | sh7_count=%d non_sh7_count=%d",
        len(sh7_documents), len(non_sh7_documents),
    )

    # Build lookup tables once — O(n) per document, O(1) per lookup
    exact_map, stem_map = _build_lookup(non_sh7_documents)

    document_groups: list[DocumentGroup] = []
    unmatched_attachment_refs: dict[str, list[str]] = {}
    pipeline_errors: list[dict] = list(state.get("pipeline_errors") or [])

    for sh7_doc in sh7_documents:
        sh7_filename = sh7_doc.file_metadata.filename
        try:
            group, unmatched = _resolve_one_sh7(sh7_doc, exact_map, stem_map)
        except Exception as exc:  # noqa: BLE001
            pipeline_errors.append({
                "filename": sh7_filename,
                "error": str(exc),
                "stage": "relationship_resolver",
            })
            logger.error(
                "Relationship resolution crashed for %s: %s", sh7_filename, exc
            )
            continue

        document_groups.append(group)
        if unmatched:
            unmatched_attachment_refs[sh7_filename] = unmatched

    logger.info(
        "Relationship Resolver complete | groups=%d unmatched_sh7s=%d",
        len(document_groups), len(unmatched_attachment_refs),
    )

    completed = list(state.get("completed_stages") or [])
    completed.append("relationship_resolver")

    state["document_groups"] = document_groups
    state["unmatched_attachment_refs"] = unmatched_attachment_refs
    state["pipeline_errors"] = pipeline_errors
    state["completed_stages"] = completed
    return state
