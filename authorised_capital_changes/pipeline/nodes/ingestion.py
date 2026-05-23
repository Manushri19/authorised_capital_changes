"""
Node 1 — Ingestion
==================
Pure file I/O; no LLM involved.

Responsibility:
  - Iterate every .md file in the flat input folder (state["input_folder"]).
  - Build a FileMetadata object for each readable file.
  - On any read failure, append a structured error dict to state["pipeline_errors"]
    and continue — the pipeline is never halted by a single bad file.

Output key: state["raw_files"]  (list[FileMetadata])
"""

from __future__ import annotations

import os
import logging
from pathlib import Path

from authorised_capital_changes.schemas.document import FileMetadata
from authorised_capital_changes.schemas.pipeline_state import PipelineState
from authorised_capital_changes.services.document_parser import read_md_file

logger = logging.getLogger(__name__)


def run_ingestion(state: PipelineState) -> PipelineState:
    """
    Ingestion node entry-point called by the LangGraph runner.

    Reads all Markdown files from *state["input_folder"]* into
    *state["raw_files"]*.  Files that cannot be read are recorded in
    *state["pipeline_errors"]* and skipped — processing continues for all
    remaining files.

    Args:
        state: Mutable pipeline state dict.  Must contain ``input_folder``.

    Returns:
        Updated state with ``raw_files`` populated and ``completed_stages``
        extended with ``"ingestion"``.
    """
    input_folder = Path(state["input_folder"])

    logger.info("Ingestion started | folder=%s", input_folder)

    raw_files: list[FileMetadata] = []
    errors: list[dict] = list(state.get("pipeline_errors") or [])

    # Validate the folder itself before iterating.
    if not input_folder.exists():
        errors.append({
            "filename": str(input_folder),
            "error": f"Input folder does not exist: {input_folder}",
            "stage": "ingestion",
        })
        logger.error("Input folder missing: %s", input_folder)
        state["raw_files"] = raw_files
        state["pipeline_errors"] = errors
        return state

    if not input_folder.is_dir():
        errors.append({
            "filename": str(input_folder),
            "error": f"Input path is not a directory: {input_folder}",
            "stage": "ingestion",
        })
        logger.error("Input path is not a directory: %s", input_folder)
        state["raw_files"] = raw_files
        state["pipeline_errors"] = errors
        return state

    # Collect .md files; sorting ensures deterministic ordering across runs.
    md_files = sorted(input_folder.glob("*.md"))

    if not md_files:
        logger.warning("No .md files found in %s", input_folder)

    for md_path in md_files:
        filename = md_path.name
        try:
            raw_content = read_md_file(md_path)
            if raw_content is None:
                raise IOError(f"Failed to read markdown file {filename}")
                
            file_size_bytes = md_path.stat().st_size

            raw_files.append(
                FileMetadata(
                    filename=filename,
                    filepath=str(md_path.resolve()),
                    raw_content=raw_content,
                    file_size_bytes=file_size_bytes,
                )
            )
            logger.debug("Ingested: %s (%d bytes)", filename, file_size_bytes)

        except Exception as exc:  # noqa: BLE001 — intentionally broad; log & continue
            errors.append({
                "filename": filename,
                "error": str(exc),
                "stage": "ingestion",
            })
            logger.warning("Failed to read %s: %s", filename, exc)

    logger.info(
        "Ingestion complete | files_read=%d errors=%d",
        len(raw_files),
        len(errors) - len(state.get("pipeline_errors") or []),
    )

    # Extend completed_stages without mutating the original list reference.
    completed = list(state.get("completed_stages") or [])
    completed.append("ingestion")

    state["raw_files"] = raw_files
    state["pipeline_errors"] = errors
    state["completed_stages"] = completed
    return state
