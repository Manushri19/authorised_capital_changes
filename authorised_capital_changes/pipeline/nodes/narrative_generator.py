"""
Node 8 — Narrative Generator (narrative_generator.py)
======================================================
1. Formats display dates for HTML rendering without mutating state.
2. Collects flags sequentially left-to-right, top-to-bottom.
3. Builds the DiscrepancyReport.
4. Outputs final_table_rows.json, discrepancy_report.json, and capital_table.html.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime

from authorised_capital_changes.schemas.capital_event import CapitalTableRow
from authorised_capital_changes.schemas.output import DiscrepancyReport, FlagEntry
from authorised_capital_changes.schemas.pipeline_state import PipelineState
from authorised_capital_changes.schemas.validation import ValidationReport
from authorised_capital_changes.services.template_engine import render_capital_table

logger = logging.getLogger(__name__)

def _format_display_date(val: str | date | None) -> str:
    """
    Format date object or isoformat string to 'Month DD, YYYY' (e.g. 'November 17, 2016').
    """
    if val == "On incorporation" or not val:
        return str(val) if val else "-"
    
    if isinstance(val, str):
        try:
            d = date.fromisoformat(val)
        except ValueError:
            return val
    else:
        d = val
        
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def _extract_conflicting_doc(msg: str | None) -> str | None:
    if not msg:
        return None
    if "Conflicting:" in msg:
        parts = msg.split("Conflicting:")
        if len(parts) > 1:
            conf_part = parts[1].strip()
            # typically "DocName=Value."
            return conf_part.split("=")[0]
    return None


def run_narrative_generator(state: PipelineState) -> PipelineState:
    logger.info("Narrative Generator started")

    capital_rows: list[CapitalTableRow] = list(state.get("capital_table_rows") or [])
    val_reports: list[ValidationReport] = list(state.get("validation_reports") or [])

    flag_entries: list[FlagEntry] = []
    seen_flags: dict[str, int] = {}
    flag_counter = 1

    html_rows = []

    # Step 1: Collect and number all flags (Left to Right, Top to Bottom)
    for row in capital_rows:
        display_date = _format_display_date(row.meeting_date.value)
        
        fields_to_check = [
            ("meeting_date", row.meeting_date),
            ("authorised_from", row.authorised_from),
            ("authorised_to", row.authorised_to),
            ("meeting_type", row.meeting_type),
        ]
        
        for field_name, fv in fields_to_check:
            if fv.flag_code:
                if fv.flag_code not in seen_flags:
                    seen_flags[fv.flag_code] = flag_counter
                    flag_counter += 1
                    
                    conflicting_doc = _extract_conflicting_doc(fv.flag_message)
                    entry = FlagEntry(
                        flag_code=fv.flag_code,
                        row_number=row.row_number,
                        field_name=field_name,
                        flag_message=fv.flag_message or "",
                        source_document=fv.source_document or "unknown",
                        conflicting_document=conflicting_doc
                    )
                    flag_entries.append(entry)
                    
        html_rows.append((row, display_date))

    # Step 3: Assemble DiscrepancyReport
    arithmetic_failures = []
    continuity_failures = []
    cross_doc_conflicts = []
    duplicate_sh7s = []
    
    for r in val_reports:
        for ac in r.arithmetic_checks:
            if not ac.passed:
                arithmetic_failures.append(ac.model_dump())
        for cc in r.continuity_checks:
            if not cc.passed:
                continuity_failures.append(cc.model_dump())
        for cdc in r.cross_document_checks:
            if not cdc.passed:
                cross_doc_conflicts.append(cdc.model_dump())
        for dc in r.duplicate_checks:
            duplicate_sh7s.append(dc.model_dump())

    disc_rep_state = state.get("discrepancy_report")
    corroborations = []
    if disc_rep_state is not None:
        if isinstance(disc_rep_state, dict):
            corroborations = disc_rep_state.get("corroborations") or []
        else:
            corroborations = getattr(disc_rep_state, "corroborations", [])

    report = DiscrepancyReport(
        run_id=state.get("run_id") or "unknown_run",
        generated_at=datetime.utcnow().isoformat() + "Z",
        total_documents_processed=len(state.get("raw_files") or []),
        sh7_documents_found=len(state.get("sh7_documents") or []),
        sh7_documents_extracted=len(state.get("extracted_sh7s") or []),
        sh7_documents_assembled=len(capital_rows) - 1 if len(capital_rows) > 0 else 0,
        sh7_documents_blocked=len(state.get("sh7s_blocked_by_validation") or []),
        flags=flag_entries,
        arithmetic_failures=arithmetic_failures,
        continuity_failures=continuity_failures,
        cross_document_conflicts=cross_doc_conflicts,
        duplicate_sh7s=duplicate_sh7s,
        unmatched_attachments=state.get("unmatched_attachment_refs") or {},
        blocked_sh7s=[{"filename": f} for f in (state.get("sh7s_blocked_by_validation") or [])],
        corroborations=corroborations
    )

    # Step 4: Write outputs
    out_dir = os.path.join(os.getcwd(), "data", "outputs")
    os.makedirs(out_dir, exist_ok=True)
    
    table_json_path = os.path.join(out_dir, "capital_table.json")
    with open(table_json_path, "w", encoding="utf-8") as f:
        json.dump([row.model_dump() for row in capital_rows], f, indent=2, default=str)
        
    report_json_path = os.path.join(out_dir, "discrepancy_report.json")
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2, default=str)

    html_content = render_capital_table(
        html_rows=html_rows,
        flag_map=seen_flags,
        flags=flag_entries
    )
    
    html_path = os.path.join(out_dir, "capital_table.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    state["final_table_rows"] = capital_rows
    state["discrepancy_report"] = report
    completed = list(state.get("completed_stages") or [])
    completed.append("narrative_generator")
    state["completed_stages"] = completed

    logger.info("Narrative Generator complete")
    return state
