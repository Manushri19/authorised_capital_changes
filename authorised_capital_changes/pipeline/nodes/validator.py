"""
Node 6 — Validator (validator.py)
==================================
Validates all extracted SH-7 records against each other and against their
attached supporting documents (board resolution, EGM resolution, MOA).

Processing steps (executed in order):
  1. Sort extracted SH-7s chronologically by meeting_date.
  2. Arithmetic check  — Field 6 "Total addition" vs Field 4(a)(i) values.
  3. Continuity check  — each event's existing capital == previous event's
                         revised capital.  Blocking on failure.
  4. Cross-document check — date and capital-amount agreement with
                            board / EGM resolution extractions.
  5. Duplicate check   — identical meeting_date across two SH-7s → block both.

Flag codes are assigned sequentially (FLAG_001, FLAG_002 …) across ALL events
in chronological order, shared between step 2 (non-blocking) and step 4
(non-blocking or blocking).

Output keys added to state:
  - validation_reports          list[ValidationReport]
  - sh7s_blocked_by_validation  list[str]   (filenames of blocked SH-7s)
  - sh7s_passed_validation      list[str]   (filenames of passed SH-7s)
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Any

from authorised_capital_changes.schemas.attachment import (
    BoardResolutionExtraction,
    EGMResolutionExtraction,
    MOAExtraction,
)
from authorised_capital_changes.schemas.pipeline_state import (
    AttachmentExtractionBundle,
    PipelineState,
)
from authorised_capital_changes.schemas.sh7 import SH7Extraction
from authorised_capital_changes.schemas.validation import (
    ArithmeticCheckResult,
    ContinuityCheckResult,
    CrossDocumentCheckResult,
    DuplicateSH7CheckResult,
    ValidationReport,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clean_decimal(raw: str) -> Decimal | None:
    """Strip Indian-style commas and whitespace, return Decimal or None."""
    if not raw:
        return None
    cleaned = re.sub(r"[,\s]", "", raw.strip())
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


# Field-6 "Total addition" line patterns (covers both plain text and HTML).

def _bundle_for_sh7(
    sh7_filename: str,
    bundles: list[AttachmentExtractionBundle],
) -> AttachmentExtractionBundle | None:
    """Return the AttachmentExtractionBundle whose sh7_filename matches."""
    for b in bundles:
        if b["sh7_filename"] == sh7_filename:
            return b
    return None


def _fmt_flag(counter: int) -> str:
    """Format a sequential flag code: FLAG_001, FLAG_002 …"""
    return f"FLAG_{counter:03d}"


# ---------------------------------------------------------------------------
# Step 2 — Arithmetic check (per SH-7, non-blocking)
# ---------------------------------------------------------------------------

def _run_arithmetic_check(
    sh7: SH7Extraction,
    flag_counter: int,
    report_flags: list[str],
    report_non_blocking: list[str],
) -> tuple[ArithmeticCheckResult, int]:
    """
    Extract Field-6 difference_addition from SH7Extraction and verify:
        existing + difference == revised

    Returns (ArithmeticCheckResult, updated_flag_counter).
    Non-blocking on failure — flag is appended but row is NOT blocked.
    """
    difference = sh7.difference_addition
    existing = sh7.existing_authorised_capital
    revised = sh7.revised_authorised_capital

    if difference is None:
        # Cannot perform arithmetic check — treat as inconclusive (not a failure)
        result = ArithmeticCheckResult(
            sh7_filename=sh7.source_filename or "",
            existing=existing,
            difference=Decimal("0"),
            revised=revised,
            computed_revised=existing,   # sentinel: unknown
            passed=True,                 # indeterminate → don't flag
            discrepancy_amount=None,
        )
        logger.warning(
            "Arithmetic check: could not extract Field-6 total addition from %s",
            sh7.source_filename,
        )
        return result, flag_counter

    computed = existing + difference
    passed = computed == revised
    discrepancy = abs(computed - revised) if not passed else None

    if not passed:
        flag_code = _fmt_flag(flag_counter)
        flag_counter += 1
        msg = (
            f"{flag_code} | Arithmetic mismatch in {sh7.source_filename or 'unknown'}: "
            f"existing({existing}) + addition({difference}) = {computed} "
            f"≠ revised({revised}). Discrepancy: {discrepancy}. "
            "Non-blocking — revised_authorised_capital used as-is."
        )
        report_flags.append(flag_code)
        report_non_blocking.append(msg)
        logger.warning(msg)

    result = ArithmeticCheckResult(
        sh7_filename=sh7.source_filename or "",
        existing=existing,
        difference=difference,
        revised=revised,
        computed_revised=computed,
        passed=passed,
        discrepancy_amount=discrepancy,
    )
    return result, flag_counter


# ---------------------------------------------------------------------------
# Step 3 — Continuity check (across SH-7s, blocking on failure)
# ---------------------------------------------------------------------------

def _run_continuity_checks(
    sorted_sh7s: list[SH7Extraction],
    moa_bundle: AttachmentExtractionBundle | None,
    blocking_errors: dict[str, list[str]],
    blocked_set: set[str],
    discrepancy_corroborations: list[dict],
) -> list[ContinuityCheckResult]:
    """
    Event 1 (index 0): ground-truth anchor — no upstream continuity check.
    Optional MOA corroboration for Event 1 only.
    Events 2–N: existing_authorised_capital must equal previous revised_capital.
    """
    results: list[ContinuityCheckResult] = []

    # --- MOA corroboration for Event 1 only ---
    if moa_bundle and moa_bundle.get("moa"):
        moa: MOAExtraction = moa_bundle["moa"]
        if moa.incorporation_capital is not None and sorted_sh7s:
            agreed = moa.incorporation_capital == sorted_sh7s[0].existing_authorised_capital
            corroboration: dict[str, Any] = {
                "check": "MOA Clause V vs SH-7 Event 1 existing capital",
                "result": "AGREED" if agreed else "DISAGREED",
                "moa_figure": str(moa.incorporation_capital),
                "sh7_figure": str(sorted_sh7s[0].existing_authorised_capital),
                "source_moa": moa.source_filename,
                "source_sh7": sorted_sh7s[0].source_filename,
            }
            if not agreed:
                corroboration["note"] = "Non-blocking. Does not affect output table."
            discrepancy_corroborations.append(corroboration)
            logger.info(
                "MOA corroboration: %s | moa=%s sh7=%s",
                corroboration["result"],
                moa.incorporation_capital,
                sorted_sh7s[0].existing_authorised_capital,
            )

    # --- Continuity across events ---
    for i, sh7 in enumerate(sorted_sh7s):
        if i == 0:
            continue  # anchor event — no upstream check

        prev_sh7 = sorted_sh7s[i - 1]
        expected_from = prev_sh7.revised_authorised_capital
        actual_from = sh7.existing_authorised_capital
        passed = expected_from == actual_from
        filename = sh7.srn or f"event_{i + 1}"

        result = ContinuityCheckResult(
            event_index=i + 1,
            sh7_filename=filename,
            expected_from=expected_from,
            actual_from=actual_from,
            passed=passed,
            source_of_expected=prev_sh7.source_filename or f"event_{i}",
        )
        results.append(result)

        if not passed:
            err = (
                f"Continuity BLOCKED | Event {i + 1} ({filename}): "
                f"expected existing_capital={expected_from} "
                f"(from {prev_sh7.source_filename}), found {actual_from}."
            )
            blocking_errors.setdefault(filename, []).append(err)
            blocked_set.add(filename)
            logger.error(err)

    return results


# ---------------------------------------------------------------------------
# Step 4 — Cross-document checks (per DocumentGroup, non/blocking)
# ---------------------------------------------------------------------------

def _cross_check_field(
    check_type: str,
    event_index: int,
    sh7_filename: str,
    sh7_value: str,
    attachments: dict[str, str],   # {doc_name: value_str}
    flag_counter: int,
    report_flags: list[str],
    report_non_blocking: list[str],
    report_blocking: list[str],
    blocked_set: set[str],
    cross_results: list[CrossDocumentCheckResult],
) -> int:
    """
    Compare sh7_value against each available attachment value.
    Disagreement rules:
      - SH-7 disagrees with ONE attachment but agrees with another → non-blocking flag.
      - SH-7 disagrees with ALL available attachments → blocking error.
    Returns updated flag_counter.
    """
    if not attachments:
        return flag_counter

    agreeing: list[str] = []
    conflicting_docs: list[tuple[str, str]] = []  # (doc_name, value)

    for doc_name, att_value in attachments.items():
        if att_value is None:
            continue
        # Normalise to Decimal for capital checks; string equality for dates
        if check_type == "CAPITAL_AMOUNT":
            sh7_dec = _clean_decimal(sh7_value)
            att_dec = _clean_decimal(att_value)
            match = sh7_dec is not None and att_dec is not None and sh7_dec == att_dec
        else:
            match = sh7_value.strip() == att_value.strip()

        if match:
            agreeing.append(doc_name)
        else:
            conflicting_docs.append((doc_name, att_value))

    if not conflicting_docs:
        return flag_counter  # all agree — nothing to report

    # Determine blocking vs non-blocking
    all_conflict = len(agreeing) == 0

    for conf_doc, conf_value in conflicting_docs:
        flag_code = _fmt_flag(flag_counter)
        flag_counter += 1
        report_flags.append(flag_code)

        result = CrossDocumentCheckResult(
            event_index=event_index,
            sh7_filename=sh7_filename,
            check_type=check_type,
            sh7_value=sh7_value,
            conflicting_document=conf_doc,
            conflicting_value=conf_value,
            agreeing_documents=agreeing,
            passed=False,
            flag_code=flag_code,
        )
        cross_results.append(result)

        if all_conflict:
            err = (
                f"{flag_code} | {check_type} BLOCKING | {sh7_filename}: SH-7 "
                f"value ({sh7_value}) disagrees with ALL attachments. "
                f"Conflicting: {conf_doc}={conf_value}. "
                "Blocked — SH-7 value disagrees with ALL attachments. "
                f"Conflicting: {conf_doc}={conf_value}."
            )
            report_blocking.append(err)
            blocked_set.add(sh7_filename)
            logger.error(err)
        else:
            msg = (
                f"{flag_code} | {check_type} non-blocking | {sh7_filename}: "
                f"SH-7 value ({sh7_value}) disagrees with {conf_doc} "
                f"({conf_value}) but agrees with {agreeing}."
            )
            report_non_blocking.append(msg)
            logger.warning(msg)

    return flag_counter


def _run_cross_document_checks(
    sh7: SH7Extraction,
    bundle: AttachmentExtractionBundle | None,
    flag_counter: int,
    report_flags: list[str],
    report_non_blocking: list[str],
    report_blocking: list[str],
    blocked_set: set[str],
    cross_results: list[CrossDocumentCheckResult],
    event_index: int,
) -> int:
    """
    Run date check and capital-amount check for one SH-7 against its bundle.
    meeting_type is NEVER compared between ClassifiedDocument.document_type and
    EGMResolutionExtraction.meeting_type — they serve different semantic roles.
    """
    if bundle is None:
        return flag_counter

    sh7_filename = sh7.source_filename or "unknown_sh7"
    sh7_date_str = sh7.meeting_date.isoformat()
    sh7_capital_str = str(sh7.revised_authorised_capital)

    board: BoardResolutionExtraction | None = bundle.get("board_resolution")
    egm: EGMResolutionExtraction | None = bundle.get("egm_resolution")

    # Build attachment value maps (only populated if the extraction exists)
    date_attachments: dict[str, str] = {}
    capital_attachments: dict[str, str] = {}

    if board:
        bd_name = board.source_filename
        if board.meeting_date:
            date_attachments[bd_name] = board.meeting_date.isoformat()
        if board.resolved_capital_amount is not None:
            capital_attachments[bd_name] = str(board.resolved_capital_amount)

    if egm:
        eg_name = egm.source_filename
        if egm.meeting_date:
            date_attachments[eg_name] = egm.meeting_date.isoformat()
        if egm.resolved_capital_amount is not None:
            capital_attachments[eg_name] = str(egm.resolved_capital_amount)

    # Date check
    flag_counter = _cross_check_field(
        check_type="DATE",
        event_index=event_index,
        sh7_filename=sh7_filename,
        sh7_value=sh7_date_str,
        attachments=date_attachments,
        flag_counter=flag_counter,
        report_flags=report_flags,
        report_non_blocking=report_non_blocking,
        report_blocking=report_blocking,
        blocked_set=blocked_set,
        cross_results=cross_results,
    )

    # Capital amount check
    flag_counter = _cross_check_field(
        check_type="CAPITAL_AMOUNT",
        event_index=event_index,
        sh7_filename=sh7_filename,
        sh7_value=sh7_capital_str,
        attachments=capital_attachments,
        flag_counter=flag_counter,
        report_flags=report_flags,
        report_non_blocking=report_non_blocking,
        report_blocking=report_blocking,
        blocked_set=blocked_set,
        cross_results=cross_results,
    )

    return flag_counter


# ---------------------------------------------------------------------------
# Step 5 — Duplicate check (blocking)
# ---------------------------------------------------------------------------

def _run_duplicate_check(
    sorted_sh7s: list[SH7Extraction],
    blocked_set: set[str],
) -> list[DuplicateSH7CheckResult]:
    """
    Detect SH-7s sharing the same meeting_date.
    Both duplicates are blocked.
    Uses post-extraction meeting_date values (more reliable than ingestion hints).
    """
    date_map: dict[str, list[str]] = defaultdict(list)
    for sh7 in sorted_sh7s:
        date_map[sh7.meeting_date.isoformat()].append(sh7.source_filename or "unknown")

    results: list[DuplicateSH7CheckResult] = []
    for date_str, filenames in date_map.items():
        if len(filenames) > 1:
            for fn in filenames:
                blocked_set.add(fn)
            result = DuplicateSH7CheckResult(
                meeting_date=sorted_sh7s[0].meeting_date.__class__.fromisoformat(date_str),
                sh7_filenames=filenames,
                routed_to_human_review=False,
            )
            results.append(result)
            logger.error(
                "Duplicate SH-7s detected for date %s: %s → both blocked.",
                date_str,
                filenames,
            )
    return results


# ---------------------------------------------------------------------------
# Node entry-point
# ---------------------------------------------------------------------------

def run_validator(state: PipelineState) -> PipelineState:
    """
    Validator node entry-point called by the LangGraph runner.

    Args:
        state: Mutable pipeline state dict. Must contain:
               - extracted_sh7s          list[SH7Extraction]
               - attachment_bundles      list[AttachmentExtractionBundle]
               - document_groups        list[DocumentGroup]  (for raw_content)
               - pipeline_errors        list[dict]

    Returns:
        Updated state with:
          - validation_reports          list[ValidationReport]
          - sh7s_blocked_by_validation  list[str]
          - sh7s_passed_validation      list[str]
          - completed_stages            extended with "validator"
    """
    extracted_sh7s: list[SH7Extraction] = list(state.get("extracted_sh7s") or [])
    bundles: list[AttachmentExtractionBundle] = list(state.get("attachment_bundles") or [])
    document_groups = list(state.get("document_groups") or [])
    pipeline_errors: list[dict] = list(state.get("pipeline_errors") or [])



    # -- Step 1: Sort SH-7s chronologically by meeting_date --
    sorted_sh7s = sorted(extracted_sh7s, key=lambda x: x.meeting_date)
    logger.info("Validator started | sh7_count=%d", len(sorted_sh7s))

    # Shared mutable state across checks
    blocked_set: set[str] = set()
    flag_counter = 1  # sequential, shared across ALL events and check types
    # Extract existing corroborations safely (dict vs Pydantic model)
    disc_rep = state.get("discrepancy_report")
    if disc_rep is None:
        all_corroborations: list[dict] = []
    elif isinstance(disc_rep, dict):
        all_corroborations: list[dict] = list(disc_rep.get("corroborations") or [])
    else:
        all_corroborations: list[dict] = list(getattr(disc_rep, "corroborations", []))

    # Per-SH7 aggregation containers
    per_sh7_arithmetic: dict[str, list[ArithmeticCheckResult]] = defaultdict(list)
    per_sh7_cross: dict[str, list[CrossDocumentCheckResult]] = defaultdict(list)
    per_sh7_flags: dict[str, list[str]] = defaultdict(list)
    per_sh7_non_blocking: dict[str, list[str]] = defaultdict(list)
    per_sh7_blocking: dict[str, list[str]] = defaultdict(list)
    continuity_results: list[ContinuityCheckResult] = []

    # -- Step 2: Arithmetic check (per SH-7) --
    for sh7 in sorted_sh7s:
        fn = sh7.source_filename or "unknown"

        arith_result, flag_counter = _run_arithmetic_check(
            sh7=sh7,
            flag_counter=flag_counter,
            report_flags=per_sh7_flags[fn],
            report_non_blocking=per_sh7_non_blocking[fn],
        )
        per_sh7_arithmetic[fn].append(arith_result)

    # -- Step 3: Continuity check (across SH-7s) --
    # Find the MOA bundle for Event 1 (index 0)
    moa_bundle: AttachmentExtractionBundle | None = None
    if sorted_sh7s:
        moa_bundle = _bundle_for_sh7(sorted_sh7s[0].source_filename or "", bundles)

    # Continuity blocking errors keyed by SH-7 identifier
    continuity_block_errors: dict[str, list[str]] = {}
    continuity_results = _run_continuity_checks(
        sorted_sh7s=sorted_sh7s,
        moa_bundle=moa_bundle,
        blocking_errors=continuity_block_errors,
        blocked_set=blocked_set,
        discrepancy_corroborations=all_corroborations,
    )

    # Merge continuity blocking errors into per-sh7 blocking lists
    for fn, errs in continuity_block_errors.items():
        per_sh7_blocking[fn].extend(errs)

    # -- Step 4: Cross-document checks (per DocumentGroup) --
    for i, sh7 in enumerate(sorted_sh7s):
        fn = sh7.source_filename or "unknown"
        bundle = _bundle_for_sh7(fn, bundles)
        flag_counter = _run_cross_document_checks(
            sh7=sh7,
            bundle=bundle,
            flag_counter=flag_counter,
            report_flags=per_sh7_flags[fn],
            report_non_blocking=per_sh7_non_blocking[fn],
            report_blocking=per_sh7_blocking[fn],
            blocked_set=blocked_set,
            cross_results=per_sh7_cross[fn],
            event_index=i + 1,
        )

    # -- Step 5: Definitive duplicate check --
    duplicate_results = _run_duplicate_check(
        sorted_sh7s=sorted_sh7s,
        blocked_set=blocked_set,
    )

    # -- Assemble ValidationReport per SH-7 --
    validation_reports: list[ValidationReport] = []
    for sh7 in sorted_sh7s:
        fn = sh7.source_filename or "unknown"
        blocking = per_sh7_blocking.get(fn, [])

        validation_passed = fn not in blocked_set

        report = ValidationReport(
            sh7_filename=fn,
            arithmetic_checks=per_sh7_arithmetic.get(fn, []),
            continuity_checks=[r for r in continuity_results if r.sh7_filename == fn],
            cross_document_checks=per_sh7_cross.get(fn, []),
            duplicate_checks=duplicate_results,
            validation_passed=validation_passed,
            blocking_errors=per_sh7_blocking.get(fn, []),
            non_blocking_flags=per_sh7_non_blocking.get(fn, []),
        )
        validation_reports.append(report)

    # Determine passed / blocked
    blocked_filenames = list(blocked_set)
    passed_filenames = [
        (sh7.source_filename or "unknown")
        for sh7 in sorted_sh7s
        if (sh7.source_filename or "unknown") not in blocked_set
    ]

    logger.info(
        "Validator complete | passed=%d blocked=%d flags_issued=%d",
        len(passed_filenames),
        len(blocked_filenames),
        flag_counter - 1,
    )

    # -- Update discrepancy_report corroborations if it exists --
    if disc_rep is not None:
        if isinstance(disc_rep, dict):
            disc_rep["corroborations"] = all_corroborations
        else:
            disc_rep.corroborations = all_corroborations

    completed = list(state.get("completed_stages") or [])
    completed.append("validator")

    state["validation_reports"] = validation_reports
    state["sh7s_blocked_by_validation"] = blocked_filenames
    state["sh7s_passed_validation"] = passed_filenames
    state["pipeline_errors"] = pipeline_errors
    state["completed_stages"] = completed
    return state
