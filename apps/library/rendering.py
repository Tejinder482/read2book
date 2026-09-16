"""Render PDF pages to images so figures/diagrams appear in the reader."""
from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium
from django.conf import settings


def page_render_path(book_id: int, page_number: int, scale: int = 2) -> Path:
    return (
        Path(settings.MEDIA_ROOT)
        / "page_renders"
        / str(book_id)
        / f"p{page_number}_s{scale}.png"
    )


def render_book_page(book_file_path: str, book_id: int, page_number: int, scale: float = 2.0) -> Path:
    """
    Rasterize a PDF page to PNG (includes all images, diagrams, and layout).
    Results are cached under MEDIA_ROOT/page_renders/.
    """
    if page_number < 1:
        raise ValueError("page_number must be >= 1")

    out = page_render_path(book_id, page_number, scale=int(scale))
    if out.exists() and out.stat().st_size > 0:
        return out

    out.parent.mkdir(parents=True, exist_ok=True)
    pdf = pdfium.PdfDocument(book_file_path)
    try:
        if page_number > len(pdf):
            raise ValueError(f"Page {page_number} out of range ({len(pdf)} pages)")
        page = pdf[page_number - 1]
        bitmap = page.render(scale=scale)
        pil_image = bitmap.to_pil()
        # Convert to RGB so PNG is widely compatible
        if pil_image.mode not in ("RGB", "L"):
            pil_image = pil_image.convert("RGB")
        pil_image.save(out, format="PNG", optimize=True)
    finally:
        pdf.close()

    return out
