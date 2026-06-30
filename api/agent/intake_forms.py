"""Predefined intake form templates per module."""

from __future__ import annotations

from typing import Any

INTAKE_FORMS: dict[str, dict[str, Any]] = {
    "bom_analyzer": {
        "module_type": "bom_analyzer",
        "title": "BOM Analyzer",
        "description": "Upload a bill of materials and provide a product name.",
        "fields": [
            {
                "name": "file_upload",
                "label": "BOM file",
                "type": "file_upload",
                "required": True,
                "accept": ".csv,.xlsx,.xls",
            },
            {
                "name": "product_name",
                "label": "Product name",
                "type": "text",
                "required": True,
                "placeholder": "e.g. Organic Cotton T-Shirt",
            },
        ],
    },
    "gap_analyzer": {
        "module_type": "gap_analyzer",
        "title": "Gap Analyzer",
        "description": "Provide company profile details for Scope 3 gap analysis.",
        "fields": [
            {
                "name": "company_name",
                "label": "Company name",
                "type": "text",
                "required": True,
            },
            {
                "name": "size",
                "label": "Company size",
                "type": "dropdown",
                "required": True,
                "options": ["1-100", "100-500", "500-5000", "5000+"],
            },
            {
                "name": "sector",
                "label": "Sector",
                "type": "text",
                "required": True,
                "placeholder": "e.g. Apparel",
            },
            {
                "name": "geography",
                "label": "Geography",
                "type": "text",
                "required": True,
                "placeholder": "e.g. United States",
            },
            {
                "name": "products",
                "label": "Products",
                "type": "textarea",
                "required": True,
                "placeholder": "List key products or product categories",
            },
        ],
    },
    "supplier_copilot": {
        "module_type": "supplier_copilot",
        "title": "Supplier Copilot",
        "description": "Select a saved product analysis and number of suppliers to rank.",
        "fields": [
            {
                "name": "product_id",
                "label": "Product",
                "type": "dropdown",
                "required": True,
                "source": "saved_analyses",
            },
            {
                "name": "top_n",
                "label": "Top N suppliers",
                "type": "number",
                "required": True,
                "default": 5,
                "min": 1,
                "max": 20,
            },
        ],
    },
}


def get_intake_form(module: str) -> dict[str, Any] | None:
    """Return the intake form schema for a module, or None if unknown."""
    return INTAKE_FORMS.get(module)
