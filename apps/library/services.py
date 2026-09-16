"""PDF processing pipeline — expandable for OCR / embeddings later."""
from __future__ import annotations

import re
from pathlib import Path

from django.utils import timezone
from pypdf import PdfReader

from .models import Book, Chapter, Page, ProcessingJob


def _default_steps_status():
    return {
        key: {"label": label, "status": ProcessingJob.StepStatus.PENDING}
        for key, label in ProcessingJob.STEPS
    }


def process_book(book_id: int) -> None:
    book = Book.objects.get(pk=book_id)
    job, _ = ProcessingJob.objects.get_or_create(book=book)
    if not job.steps:
        job.steps = _default_steps_status()
        job.save(update_fields=["steps"])

    book.status = Book.Status.PROCESSING
    book.save(update_fields=["status", "updated_at"])

    try:
        _mark(job, uploaded="done", percent=8)

        path = book.file.path
        reader = PdfReader(path, strict=False)
        _mark(job, extracting="active", percent=15)

        # Faster extraction: one pass, no per-page DB until the end
        page_texts: list[str] = []
        pages_iter = reader.pages
        total_guess = len(pages_iter)
        for i, page in enumerate(pages_iter):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            page_texts.append(text.strip())
            if total_guess and i > 0 and i % 25 == 0:
                pct = 15 + int(35 * (i / total_guess))
                _mark(job, extracting="active", percent=min(pct, 48))

        total_chars = sum(len(t) for t in page_texts)
        if total_chars < 40 and len(page_texts) > 0:
            job.requires_ocr = True
            job.ocr_message = (
                "This document appears to be scanned. "
                "OCR is not enabled in Phase 1; text may be limited."
            )
            job.save(update_fields=["requires_ocr", "ocr_message", "updated_at"])

        _mark(job, extracting="done", chapters="active", percent=52)

        meta_title = (reader.metadata.title if reader.metadata else None) or ""
        if not book.title:
            book.title = (
                meta_title.strip()
                or Path(book.file.name).stem.replace("_", " ").title()
            )
        if reader.metadata and reader.metadata.author and not book.author:
            book.author = str(reader.metadata.author)

        chapters = _detect_chapters(book, page_texts, reader)
        _mark(job, chapters="done", pages="active", percent=62)

        Page.objects.filter(book=book).delete()
        page_rows = []
        for i, text in enumerate(page_texts, start=1):
            page_rows.append(
                Page(
                    book=book,
                    chapter=_chapter_for_page(chapters, i),
                    number=i,
                    text=text,
                )
            )
        Page.objects.bulk_create(page_rows, batch_size=500)

        book.page_count = len(page_rows)
        book.chapter_count = len(chapters)
        book.estimated_reading_hours = round((book.page_count * 200) / 225 / 60, 1)
        if not book.overview:
            book.overview = _template_overview(book, page_texts)
        book.status = Book.Status.READY
        book.save(
            update_fields=[
                "title",
                "author",
                "page_count",
                "chapter_count",
                "estimated_reading_hours",
                "overview",
                "status",
                "updated_at",
            ]
        )

        _mark(
            job,
            pages="done",
            index="done",
            ai_kb="done",
            finalizing="done",
            percent=100,
        )
    except Exception as exc:
        book.status = Book.Status.FAILED
        book.error_message = str(exc)[:2000]
        book.save(update_fields=["status", "error_message", "updated_at"])
        if job.current_step and job.current_step in (job.steps or {}):
            job.steps[job.current_step]["status"] = ProcessingJob.StepStatus.FAILED
            job.save(update_fields=["steps", "updated_at"])
        raise


def _mark(job: ProcessingJob, percent: int | None = None, **step_statuses: str) -> None:
    """Update multiple checklist steps in one DB write."""
    if not job.steps:
        job.steps = _default_steps_status()
    status_map = {
        "pending": ProcessingJob.StepStatus.PENDING,
        "active": ProcessingJob.StepStatus.ACTIVE,
        "done": ProcessingJob.StepStatus.DONE,
        "failed": ProcessingJob.StepStatus.FAILED,
    }
    for key, status in step_statuses.items():
        if key in job.steps:
            job.steps[key]["status"] = status_map.get(status, status)
            job.current_step = key
    if percent is not None:
        job.progress_percent = percent
    job.save(update_fields=["steps", "current_step", "progress_percent", "updated_at"])


def _detect_chapters(book: Book, page_texts: list[str], reader: PdfReader) -> list[Chapter]:
    Chapter.objects.filter(book=book).delete()
    outline_chapters: list[tuple[str, int]] = []

    try:
        outline = reader.outline or []
        for item in outline:
            if isinstance(item, list):
                continue
            title = getattr(item, "title", None) or str(item)
            try:
                page_num = reader.get_destination_page_number(item) + 1
            except Exception:
                continue
            outline_chapters.append((title.strip(), page_num))
    except Exception:
        outline_chapters = []

    if not outline_chapters:
        heading_re = re.compile(
            r"^(chapter\s+\d+|part\s+\d+|section\s+\d+|introduction|preface|appendix)[:\s].*$",
            re.I,
        )
        for i, text in enumerate(page_texts, start=1):
            first_line = (text.splitlines() or [""])[0].strip()
            if heading_re.match(first_line) and len(first_line) < 120:
                outline_chapters.append((first_line.title(), i))

    if not outline_chapters:
        total = max(len(page_texts), 1)
        step = 20
        outline_chapters = [
            (f"Section {(i // step) + 1}", i + 1) for i in range(0, total, step)
        ]

    chapters: list[Chapter] = []
    for idx, (title, start) in enumerate(outline_chapters):
        end = (
            outline_chapters[idx + 1][1] - 1
            if idx + 1 < len(outline_chapters)
            else len(page_texts)
        )
        chapters.append(
            Chapter(
                book=book,
                title=title[:255],
                order=idx,
                start_page=start,
                end_page=max(start, end),
            )
        )
    return Chapter.objects.bulk_create(chapters)


def _chapter_for_page(chapters: list[Chapter], page_number: int) -> Chapter | None:
    for ch in chapters:
        if ch.start_page <= page_number <= ch.end_page:
            return ch
    return chapters[-1] if chapters else None


def _template_overview(book: Book, page_texts: list[str]) -> str:
    sample = " ".join(page_texts[:3])[:600].replace("\n", " ")
    return (
        f"{book.title} has {book.page_count} pages across {book.chapter_count} chapters. "
        f"Estimated reading time is about {book.estimated_reading_hours} hours. "
        f"Opening excerpt: {sample}…"
        if sample
        else f"{book.title} is ready to read."
    )


def touch_last_opened(book: Book) -> None:
    book.last_opened_at = timezone.now()
    book.save(update_fields=["last_opened_at", "updated_at"])
