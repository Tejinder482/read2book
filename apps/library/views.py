from pathlib import Path

from django.http import FileResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import IsOwner

from .models import Book, Page
from .rendering import render_book_page
from .serializers import (
    BookDetailSerializer,
    BookListSerializer,
    BookUploadSerializer,
    ChapterSerializer,
    PageSerializer,
    ProcessingJobSerializer,
)
from .tasks import enqueue_book_processing
from .services import touch_last_opened

class BookViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwner]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return Book.objects.filter(owner=self.request.user).select_related(
            "processing_job"
        )

    def get_serializer_class(self):
        if self.action == "create":
            return BookUploadSerializer
        if self.action in ("retrieve", "processing"):
            return BookDetailSerializer
        return BookListSerializer

    def perform_create(self, serializer):
        book = serializer.save()
        book.status = Book.Status.PROCESSING
        book.save(update_fields=["status", "updated_at"])
        enqueue_book_processing(book.id)

    def create(self, request, *args, **kwargs):
        payload = request.data
        if request.FILES.get("file") and not payload.get("file"):
            # Rebuild so FileField always sees the upload
            payload = {
                "title": request.data.get("title", ""),
                "file": request.FILES["file"],
            }
        serializer = self.get_serializer(data=payload)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        book = serializer.instance
        return Response(
            BookDetailSerializer(book, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        book = self.get_object()
        touch_last_opened(book)
        return Response(BookDetailSerializer(book, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def processing(self, request, pk=None):
        book = self.get_object()
        job = getattr(book, "processing_job", None)
        data = {
            "book_id": book.id,
            "status": book.status,
            "error_message": book.error_message,
            "processing": ProcessingJobSerializer(job).data if job else None,
        }
        return Response(data)

    @action(detail=True, methods=["get"])
    def toc(self, request, pk=None):
        book = self.get_object()
        chapters = book.chapters.all()
        return Response(
            ChapterSerializer(chapters, many=True, context={"request": request}).data
        )

    @action(detail=True, methods=["get"], url_path=r"pages/(?P<number>[0-9]+)")
    def page(self, request, pk=None, number=None):
        book = self.get_object()
        try:
            page = book.pages.get(number=int(number))
        except Page.DoesNotExist:
            return Response({"detail": "Page not found."}, status=404)
        touch_last_opened(book)
        return Response(PageSerializer(page).data)

    @action(detail=True, methods=["get"], url_path="pdf")
    def pdf_file(self, request, pk=None):
        """Stream the original PDF (auth required) for PDF.js rendering."""
        book = self.get_object()
        if not book.file:
            return Response({"detail": "PDF file missing."}, status=404)
        path = Path(book.file.path)
        if not path.exists():
            return Response({"detail": "PDF file missing on disk."}, status=404)
        response = FileResponse(
            open(path, "rb"),
            as_attachment=False,
            filename=path.name,
            content_type="application/pdf",
        )
        response["Accept-Ranges"] = "bytes"
        response["Cache-Control"] = "private, max-age=3600"
        return response

    @action(detail=True, methods=["get"], url_path=r"pages/(?P<number>[0-9]+)/render")
    def render_page(self, request, pk=None, number=None):
        """Return a PNG of the PDF page (text + images + layout)."""
        book = self.get_object()
        page_number = int(number)
        if not book.file:
            return Response({"detail": "PDF file missing."}, status=404)
        try:
            max_page = book.page_count or 0
            if max_page and page_number > max_page:
                return Response({"detail": "Page not found."}, status=404)
            path = render_book_page(book.file.path, book.id, page_number, scale=2.5)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        except Exception as exc:
            return Response(
                {"detail": f"Could not render page: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return FileResponse(
            open(path, "rb"),
            as_attachment=False,
            filename=Path(path).name,
            content_type="image/png",
        )

    @action(detail=True, methods=["get"])
    def search(self, request, pk=None):
        book = self.get_object()
        q = (request.query_params.get("q") or "").strip()
        if not q:
            return Response({"results": []})
        pages = book.pages.filter(text__icontains=q)[:40]
        results = []
        for page in pages:
            text = page.text
            idx = text.lower().find(q.lower())
            start = max(0, idx - 80)
            end = min(len(text), idx + len(q) + 80)
            snippet = text[start:end].replace("\n", " ")
            results.append(
                {
                    "page": page.number,
                    "snippet": f"…{snippet}…" if snippet else "",
                    "chapter_id": page.chapter_id,
                }
            )
        return Response({"query": q, "results": results})
