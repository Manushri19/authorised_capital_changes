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
    pipeline_errors: list[dict]
    completed_stages: list[str]