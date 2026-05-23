"""
services/template_engine.py
===========================
Sets up the Jinja2 environment, attaches custom filters, and provides
clean APIs for rendering specific HTML outputs.
"""

import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
from authorised_capital_changes.services.document_parser import format_inr

# Determine the absolute path to the templates directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Initialize the Jinja environment
env = Environment(
    loader=FileSystemLoader(searchpath=TEMPLATES_DIR),
    autoescape=select_autoescape(['html', 'xml'])
)

# Register custom filters (for potential future use directly in the template)
env.filters["format_inr"] = format_inr

def render_capital_table(html_rows: list, flag_map: dict, flags: list) -> str:
    """
    Renders the final capital_table.html with the provided contextual data.
    """
    template = env.get_template("capital_table.html")
    return template.render(
        html_rows=html_rows,
        flag_map=flag_map,
        flags=flags
    )
