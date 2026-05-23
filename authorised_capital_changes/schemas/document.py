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