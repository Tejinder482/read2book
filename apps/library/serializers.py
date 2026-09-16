from django.conf import settings
from rest_framework import serializers

from apps.reader.models import ReadingProgress

from .models import Book, Chapter, Page, ProcessingJob


class ChapterSerializer(serializers.ModelSerializer):
    progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = (
            "id",
            "title",
            "order",
            "start_page",
            "end_page",
            "progress_percent",
        )

    def get_progress_percent(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return 0
        progress = (
            ReadingProgress.objects.filter(user=request.user, book=obj.book).first()
        )
        if not progress:
            return 0
        if progress.current_page < obj.start_page:
            return 0
        if progress.current_page >= obj.end_page:
            return 100
        span = max(obj.end_page - obj.start_page + 1, 1)
        done = progress.current_page - obj.start_page + 1
        return min(100, int(done / span * 100))


class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = ("id", "number", "text", "chapter")


class ProcessingJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessingJob
        fields = (
            "steps",
            "requires_ocr",
            "ocr_message",
            "current_step",
            "progress_percent",
            "updated_at",
        )


class BookListSerializer(serializers.ModelSerializer):
    progress_percent = serializers.SerializerMethodField()
    current_page = serializers.SerializerMethodField()
    reading_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = (
            "id",
            "title",
            "author",
            "cover",
            "page_count",
            "chapter_count",
            "status",
            "file_size",
            "estimated_reading_hours",
            "last_opened_at",
            "created_at",
            "progress_percent",
            "current_page",
            "reading_minutes",
        )

    def _progress(self, obj):
        request = self.context.get("request")
        if not request:
            return None
        return ReadingProgress.objects.filter(user=request.user, book=obj).first()

    def get_progress_percent(self, obj):
        p = self._progress(obj)
        if not p or not obj.page_count:
            return 0
        return min(100, int(p.current_page / obj.page_count * 100))

    def get_current_page(self, obj):
        p = self._progress(obj)
        return p.current_page if p else 1

    def get_reading_minutes(self, obj):
        p = self._progress(obj)
        return p.reading_seconds // 60 if p else 0


class BookDetailSerializer(BookListSerializer):
    processing = ProcessingJobSerializer(source="processing_job", read_only=True)
    file = serializers.FileField(read_only=True)

    class Meta(BookListSerializer.Meta):
        fields = BookListSerializer.Meta.fields + (
            "overview",
            "error_message",
            "processing",
            "file",
        )


class BookUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ("id", "file", "title")

    def validate_title(self, value):
        return (value or "")[:255]

    def validate_file(self, value):
        name = (getattr(value, "name", "") or "").lower()
        content_type = (getattr(value, "content_type", "") or "").lower()
        is_pdf = name.endswith(".pdf") or content_type in (
            "application/pdf",
            "application/x-pdf",
        )
        if not is_pdf:
            raise serializers.ValidationError("Only PDF files are supported.")
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if value.size > max_bytes:
            raise serializers.ValidationError(
                f"File too large. Max {settings.MAX_UPLOAD_SIZE_MB} MB."
            )
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        f = validated_data["file"]
        title = (validated_data.get("title") or f.name.rsplit(".", 1)[0])[:255]
        book = Book.objects.create(
            owner=user,
            title=title,
            file=f,
            file_size=f.size,
            status=Book.Status.UPLOADING,
        )
        job, _ = ProcessingJob.objects.get_or_create(book=book)
        if not job.steps:
            job.init_steps()
        return book
