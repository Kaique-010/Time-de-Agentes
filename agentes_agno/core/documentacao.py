from __future__ import annotations

import base64
import re
from html import unescape
from typing import Any


_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


class LeitorDocumentacao:
    """Normaliza documentação textual (html/pdf/texto) para consumo por agentes."""

    def extrair_texto(self, extras: dict[str, Any]) -> str:
        partes: list[str] = []

        texto = extras.get("documentacao_texto")
        if isinstance(texto, str) and texto.strip():
            partes.append(texto.strip())

        html = extras.get("documentacao_html")
        if isinstance(html, str) and html.strip():
            partes.append(self._clean_html(html))

        pdf_b64 = extras.get("documentacao_pdf_base64")
        if isinstance(pdf_b64, str) and pdf_b64.strip():
            pdf_text = self._extract_pdf_base64(pdf_b64)
            if pdf_text:
                partes.append(pdf_text)

        return "\n\n".join([p for p in partes if p]).strip()

    def _clean_html(self, html: str) -> str:
        text = _TAG_RE.sub(" ", html)
        text = unescape(text)
        return _SPACE_RE.sub(" ", text).strip()

    def _extract_pdf_base64(self, encoded: str) -> str:
        raw = encoded.strip()
        if raw.startswith("data:application/pdf;base64,"):
            raw = raw.split(",", 1)[1]

        try:
            payload = base64.b64decode(raw, validate=False)
        except Exception:
            return ""

        try:
            from pypdf import PdfReader  # type: ignore
        except Exception:
            return ""

        from io import BytesIO

        try:
            reader = PdfReader(BytesIO(payload))
        except Exception:
            return ""

        textos = []
        for page in reader.pages:
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            if t.strip():
                textos.append(t.strip())
        return "\n\n".join(textos).strip()
