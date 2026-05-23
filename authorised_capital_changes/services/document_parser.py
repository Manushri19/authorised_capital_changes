"""
services/document_parser.py
===========================
Utilities for parsing documents, reading text files, and handling locale-specific
formatting operations like Indian Numbering System conversions.
"""

import logging
from decimal import Decimal
from pathlib import Path

logger = logging.getLogger(__name__)

def read_md_file(filepath: str | Path) -> str | None:
    """
    Read a markdown file and return its content, or None on failure.
    """
    path = Path(filepath)
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning("Failed to read file %s: %s", filepath, exc)
        return None

def format_inr(value: Decimal | int | float | str | None) -> str:
    """
    Format a numeric value as an Indian Rupee string using the Indian Numbering System.
    (e.g. 20000000 -> ₹2,00,00,000)
    """
    if value is None:
        return ""
        
    try:
        if isinstance(value, Decimal) and value == value.to_integral_value():
            value = int(value)
        s = str(value)
    except (ValueError, TypeError, Exception):
        return str(value)
        
    if "." in s:
        integer_part, decimal_part = s.split(".")
    else:
        integer_part, decimal_part = s, ""

    if len(integer_part) > 3:
        last_3 = integer_part[-3:]
        rest = integer_part[:-3]
        chunks = []
        while len(rest) > 0:
            chunks.insert(0, rest[-2:])
            rest = rest[:-2]
        integer_part = ",".join(chunks) + "," + last_3

    if decimal_part:
        return f"₹{integer_part}.{decimal_part}"
    return f"₹{integer_part}"
