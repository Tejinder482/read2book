from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.library.models import Book, Page

from .models import Bookmark, Highlight, Note, ReadingProgress
from .serializers import (
    BookmarkSerializer,
    HighlightSerializer,
    NoteSerializer,
    ReadingProgressSerializer,
)


class HighlightViewSet(viewsets.ModelViewSet):
    serializer_class = HighlightSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Highlight.objects.filter(user=self.request.user).select_related("book", "chapter")
        book_id = self.request.query_params.get("book")
        if book_id:
            qs = qs.filter(book_id=book_id)
        return qs


class NoteViewSet(viewsets.ModelViewSet):
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Note.objects.filter(user=self.request.user).select_related("book", "chapter")
        book_id = self.request.query_params.get("book")
        if book_id:
            qs = qs.filter(book_id=book_id)
        return qs


class BookmarkViewSet(viewsets.ModelViewSet):
    serializer_class = BookmarkSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Bookmark.objects.filter(user=self.request.user).select_related("book")
        book_id = self.request.query_params.get("book")
        if book_id:
            qs = qs.filter(book_id=book_id)
        return qs


class ProgressView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, book_id):
        progress = ReadingProgress.objects.filter(
            user=request.user, book_id=book_id
        ).first()
        if not progress:
            return Response(
                {"book": book_id, "current_page": 1, "reading_seconds": 0}
            )
        return Response(ReadingProgressSerializer(progress).data)

    def put(self, request, book_id):
        try:
            book = Book.objects.get(pk=book_id, owner=request.user)
        except Book.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        page_number = int(request.data.get("current_page", 1))
        page = Page.objects.filter(book=book, number=page_number).first()
        add_seconds = int(request.data.get("add_seconds", 0))
        progress, _ = ReadingProgress.objects.get_or_create(user=request.user, book=book)
        progress.current_page = page_number
        if page:
            progress.current_chapter = page.chapter
        if add_seconds > 0:
            progress.reading_seconds += add_seconds
        progress.save()
        return Response(ReadingProgressSerializer(progress).data)
