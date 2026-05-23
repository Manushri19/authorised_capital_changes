"""
Node 7 — Assembler (assembler.py)
==================================
Builds the preliminary capital table rows from validated SH-7 extractions.
Filters out any blocked SH-7s before assembling.

Outputs:
  - capital_table_rows (list[CapitalTableRow])
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from authorised_capital_changes.schemas.attachment import EGMResolutionExtraction
from authorised_capital_changes.schemas.capital_event import CapitalTableRow, FieldValue
from authorised_capital_changes.schemas.pipeline_state import AttachmentExtractionBundle, PipelineState
from authorised_capital_changes.schemas.sh7 import SH7Extraction
from authorised_capital_changes.schemas.validation import CrossDocumentCheckResult, ValidationReport
from authorised_capital_changes.services.document_parser import format_inr

logger = logging.getLogger(__name__)


def format_capital_narrative(
    total_amount: Decimal,
    equity_count: int | None,
    equity_nominal: Decimal | None,
    preference_count: int | None = None,
    preference_nominal: Decimal | None = None
) -> str:
    total_str = format_inr(total_amount)
    
    if equity_count is None:
        return f"{total_str} (share breakdown not determinable — see footnote)"

    eq_cnt_str = format_inr(equity_count).replace("₹", "")
    eq_nom_str = format_inr(equity_nominal)
    
    narrative = f"{total_str} divided into {eq_cnt_str} Equity Shares of {eq_nom_str} each"

    if preference_count is not None and preference_count > 0:
        pref_cnt_str = format_inr(preference_count).replace("₹", "")
        pref_nom_str = format_inr(preference_nominal)
        narrative += f" and {pref_cnt_str} Preference Shares of {pref_nom_str} each"

    return narrative

    return narrative


def compute_prechange_breakdown(
    existing_total: Decimal,
    nominal_per_share: Decimal | None,
    post_change_preference_count: int | None,
    source_sh7_filename: str
) -> tuple[int | None, str]:
    if post_change_preference_count is not None and post_change_preference_count > 0:
        return None, (
            "Pre-change share breakdown cannot be derived arithmetically — "
            "preference shares present in post-change capital suggest mixed "
            "share classes may exist in pre-change capital. "
            f"Source: {source_sh7_filename} Section 9(a)"
        )

    if not nominal_per_share or nominal_per_share == Decimal("0"):
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


def _get_bundle_for_sh7(sh7: SH7Extraction, bundles: list[AttachmentExtractionBundle]) -> AttachmentExtractionBundle | None:
    for b in bundles:
        if b.get("sh7_filename") == sh7.source_filename:
            return b
    return None


def _get_validation_report_for(sh7: SH7Extraction, reports: list[ValidationReport]) -> ValidationReport | None:
    for r in reports:
        if r.sh7_filename == sh7.srn:
            return r
    return None


def _get_sh7_filename(sh7: SH7Extraction, groups: list[Any]) -> str:
    return sh7.source_filename or "unknown"


def _infer_meeting_type_from_filenames(attachment_filenames_raw: list[str]) -> str | None:
    """
    Scan the raw attachment filenames listed on the SH-7 for any file whose
    name contains the literal token 'EGM' or 'AGM' (case-insensitive).
    Returns the first match ('EGM' or 'AGM') or None if not found.
    This is a deterministic, zero-LLM fallback — no inference, just name matching.
    """
    for fname in attachment_filenames_raw:
        upper = fname.upper()
        if "EGM" in upper:
            return "EGM"
        if "AGM" in upper:
            return "AGM"
    return None


def _get_cross_doc_flag_message(val_report: ValidationReport | None, check_type: str) -> tuple[str | None, str | None]:
    if not val_report:
        return None, None
    for cross in val_report.cross_document_checks:
        if cross.check_type == check_type and not cross.passed:
            prefix = f"{cross.flag_code} |"
            # search non-blocking
            for msg in val_report.non_blocking_flags:
                if msg.startswith(prefix):
                    return cross.flag_code, msg
            # search blocking
            for msg in val_report.blocking_errors:
                if msg.startswith(prefix):
                    return cross.flag_code, msg
            
            # fallback
            return cross.flag_code, f"{cross.flag_code} | Discrepancy in {check_type}"
    return None, None


def run_assembler(state: PipelineState) -> PipelineState:
    logger.info("Assembler node started")
    
    extracted_sh7s: list[SH7Extraction] = list(state.get("extracted_sh7s") or [])
    passed_sh7_filenames: list[str] = list(state.get("sh7s_passed_validation") or [])
    bundles: list[AttachmentExtractionBundle] = list(state.get("attachment_bundles") or [])
    val_reports: list[ValidationReport] = list(state.get("validation_reports") or [])
    groups = list(state.get("document_groups") or [])

    # Filter to passed SH-7s only and sort chronologically
    valid_sh7s = [sh7 for sh7 in extracted_sh7s if (sh7.source_filename or "unknown") in passed_sh7_filenames]
    sorted_sh7s = sorted(valid_sh7s, key=lambda x: x.meeting_date)

    if not sorted_sh7s:
        logger.warning("No valid SH-7s passed validation. Assembler returning empty table.")
        state["capital_table_rows"] = []
        state["completed_stages"] = list(state.get("completed_stages") or []) + ["assembler"]
        return state

    rows: list[CapitalTableRow] = []

    # --- Build Row 0 (On Incorporation) ---
    sh7_e1 = sorted_sh7s[0]
    sh7_e1_filename = _get_sh7_filename(sh7_e1, groups)

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
            source_field_human="Existing authorised capital before first event, used as incorporation capital",
            flag_code=None,
            flag_message=None
        ),
        authorised_from=FieldValue(
            value=None,
            confirmed=True,
            source_document=sh7_e1_filename,
            source_field_machine=None,
            source_field_human=None,
            flag_code=None,
            flag_message=None
        ),
        authorised_to=FieldValue(
            value=format_capital_narrative(
                total_amount=sh7_e1.existing_authorised_capital,
                equity_count=computed_count,
                equity_nominal=sh7_e1.authorised_capital.breakdown.equity_nominal_per_share
            ),
            confirmed=computed_count is not None,
            source_document=sh7_e1_filename,
            source_field_machine="Field 4(a)(i) — Existing + Section 9(a) nominal value",
            source_field_human=source_note,
            flag_code=None if computed_count is not None else "FLAG_BREAKDOWN_UNDERIVABLE",
            flag_message=None if computed_count is not None else source_note
        ),
        meeting_type=FieldValue(
            value=None,
            confirmed=True,
            source_document=None,
            source_field_machine=None,
            source_field_human=None,
            flag_code=None,
            flag_message=None
        ),
        source_srn=None,
        source_sh7_filename=sh7_e1_filename,
        source_filing_date=None,
        has_flags=computed_count is None,
        flag_count=1 if computed_count is None else 0,
        flags=["FLAG_BREAKDOWN_UNDERIVABLE"] if computed_count is None else []
    )
    rows.append(row_0)

    # --- Build Rows 1–N ---
    for i, sh7 in enumerate(sorted_sh7s):
        bundle = _get_bundle_for_sh7(sh7, bundles) or {}
        val_report = _get_validation_report_for(sh7, val_reports)
        egm: EGMResolutionExtraction | None = bundle.get("egm_resolution")
        sh7_filename = _get_sh7_filename(sh7, groups)

        date_flag_code, date_flag_msg = _get_cross_doc_flag_message(val_report, "DATE")
        capital_flag_code, capital_flag_msg = _get_cross_doc_flag_message(val_report, "CAPITAL_AMOUNT")

        meeting_date_fv = FieldValue(
            value=sh7.meeting_date.isoformat(),
            confirmed=True,
            source_document=sh7_filename,
            source_field_machine="Field 4",
            source_field_human="Date of members' meeting, Field 4",
            flag_code=date_flag_code,
            flag_message=date_flag_msg
        )

        authorised_from_fv = FieldValue(
            value=rows[i].authorised_to.value,
            confirmed=True,
            source_document=sh7_filename,
            source_field_machine="Field 4(a)(i) — Existing",
            source_field_human="Existing authorised capital before this event",
            flag_code=None,
            flag_message=None
        )

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
            flag_code=capital_flag_code,
            flag_message=capital_flag_msg
        )

        if egm and egm.meeting_type:
            meeting_type_fv = FieldValue(
                value=egm.meeting_type,
                confirmed=True,
                source_document=egm.source_filename,
                source_field_machine="EGM/AGM Resolution operative clause",
                source_field_human="Meeting type confirmed from EGM/AGM resolution document",
                flag_code=None,
                flag_message=None
            )
        else:
            # Fallback: infer meeting type from the names of files attached to the SH-7.
            # If an attached filename contains the literal token 'EGM' or 'AGM' that is
            # sufficient to determine meeting type without any LLM involvement.
            inferred_type = _infer_meeting_type_from_filenames(sh7.attachment_filenames_raw)
            if inferred_type:
                meeting_type_fv = FieldValue(
                    value=inferred_type,
                    confirmed=True,
                    source_document=sh7_filename,
                    source_field_machine="SH-7 Attachments section — filename token",
                    source_field_human=(
                        f"Meeting type inferred from attached filename containing '{inferred_type}' "
                        "in the SH-7 Attachments section"
                    ),
                    flag_code=None,
                    flag_message=None
                )
            else:
                meeting_type_fv = FieldValue(
                    value=None,
                    confirmed=False,
                    source_document=None,
                    source_field_machine=None,
                    source_field_human=None,
                    flag_code="FLAG_MEETING_TYPE_UNCONFIRMED",
                    flag_message="AGM/EGM could not be confirmed — no EGM/AGM resolution document available and no EGM/AGM token found in attached filenames"
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
            source_srn=sh7.source_filename,
            source_sh7_filename=sh7_filename,
            source_filing_date=sh7.filing_date,
            has_flags=len(row_flags) > 0,
            flag_count=len(row_flags),
            flags=row_flags
        ))

    logger.info("Assembler complete. Generated %d rows.", len(rows))
    state["capital_table_rows"] = rows
    state["completed_stages"] = list(state.get("completed_stages") or []) + ["assembler"]
    return state
