from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from app.config import settings

INVOICE_KEYS = [
    "vendor_name",
    "vendor_email",
    "invoice_number",
    "invoice_date",
    "due_date",
    "currency",
    "subtotal",
    "tax",
    "total",
    "customer_name",
    "customer_email",
    "line_items_summary",
]


def _regex_extract(text: str) -> dict[str, dict[str, Any]]:
    """Deterministic fallback so demos work without an LLM key."""
    patterns = {
        "vendor_name": r"(?im)^(?:from|vendor|billed by)[:\s]+(.+)$",
        "vendor_email": r"(?i)[\w.+-]+@[\w.-]+\.\w+",
        "invoice_number": r"(?i)invoice\s*(?:#|no\.?|number)?\s*[:#]?\s*([A-Z0-9-]+)",
        "invoice_date": r"(?i)(?:invoice\s*)?date[:\s]+(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        "due_date": r"(?i)due(?:\s*date)?[:\s]+(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        "total": r"(?i)(?:total\s*(?:due|amount)?|amount\s*due)[:\s]*\$?\s*([\d,]+\.?\d*)",
        "subtotal": r"(?i)subtotal[:\s]*\$?\s*([\d,]+\.?\d*)",
        "tax": r"(?i)tax[:\s]*\$?\s*([\d,]+\.?\d*)",
        "customer_name": r"(?im)^(?:bill to|customer|client)[:\s]+(.+)$",
        "customer_email": r"(?i)(?:bill to|customer).*?([\w.+-]+@[\w.-]+\.\w+)",
    }
    out: dict[str, dict[str, Any]] = {}
    for key, pat in patterns.items():
        m = re.search(pat, text)
        if not m:
            continue
        val = m.group(1).strip() if m.lastindex else m.group(0).strip()
        conf = 0.72 if key in {"total", "invoice_number", "vendor_name"} else 0.55
        out[key] = {
            "value": val,
            "confidence": conf,
            "uncertain": conf < 0.65,
            "edited": False,
        }

    if "currency" not in out and "$" in text:
        out["currency"] = {"value": "USD", "confidence": 0.9, "uncertain": False, "edited": False}

    # line items: crude bullet/number lines
    lines = []
    for line in text.splitlines():
        if re.search(r"\$\s*[\d,]+\.?\d*", line) and not re.search(r"(?i)total|subtotal|tax", line):
            lines.append(line.strip())
    if lines:
        out["line_items_summary"] = {
            "value": " | ".join(lines[:8]),
            "confidence": 0.5,
            "uncertain": True,
            "edited": False,
        }

    for key in INVOICE_KEYS:
        if key not in out:
            out[key] = {"value": None, "confidence": 0.0, "uncertain": True, "edited": False}
    return out


def _llm_extract(text: str) -> dict[str, dict[str, Any]] | None:
    key = settings.llm_api_key()
    if not key:
        return None

    client_kwargs: dict[str, Any] = {"api_key": key}
    base = settings.llm_base_url()
    if base:
        client_kwargs["base_url"] = base
    client = OpenAI(**client_kwargs)

    prompt = f"""Extract invoice fields from the document below.
Return ONLY valid JSON object with these keys: {json.dumps(INVOICE_KEYS)}.
Each value must be an object: {{"value": string|number|null, "confidence": 0-1, "uncertain": boolean}}.
Mark uncertain=true when confidence < 0.7 or the field is missing/ambiguous.

DOCUMENT:
{text[:12000]}
"""
    try:
        resp = client.chat.completions.create(
            model=settings.llm_model(),
            messages=[
                {"role": "system", "content": "You extract structured invoice data. JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"
        data = json.loads(raw)
    except Exception:
        return None

    out: dict[str, dict[str, Any]] = {}
    for key in INVOICE_KEYS:
        item = data.get(key)
        if isinstance(item, dict):
            conf = float(item.get("confidence") or 0)
            out[key] = {
                "value": item.get("value"),
                "confidence": conf,
                "uncertain": bool(item.get("uncertain", conf < 0.7)),
                "edited": False,
            }
        else:
            out[key] = {
                "value": item if item is not None else None,
                "confidence": 0.4 if item is not None else 0.0,
                "uncertain": True,
                "edited": False,
            }
    return out


def extract_invoice(text: str) -> tuple[str, dict[str, dict[str, Any]], str]:
    """Returns (doc_type, fields, method)."""
    llm = _llm_extract(text)
    if llm:
        return "invoice", llm, "llm"
    return "invoice", _regex_extract(text), "regex"
