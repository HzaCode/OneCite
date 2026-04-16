# !/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Small shared helpers used by more than one pipeline stage."""


def _safe_year(date_obj):
    """Safely extract year from a CrossRef date object like {'date-parts': [[2015, 3, 1]]}."""
    if not date_obj:
        return None
    parts = date_obj.get('date-parts', [])
    if parts and isinstance(parts, list) and len(parts) > 0:
        inner = parts[0]
        if isinstance(inner, list) and len(inner) > 0:
            return inner[0]
    return None
