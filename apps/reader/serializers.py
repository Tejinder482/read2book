from rest_framework import serializers

from apps.library.models import Book, Page

from .models import Bookmark, Highlight, Note, ReadingProgress


class ReadingProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadingProgress
        fields = (
            "id",
            "book",
            "current_page",
            "current_chapter",
            "reading_seconds",
            "updated_at",
        )
        read_only_fields = ("id", "updated_at")


class HighlightSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)

    class Meta:
        model = Highlight
        fields = (
            "id",
            "book",
            "book_title",
            "chapter",
            "page",
            "page_number",
            "selected_text",
            "color",
            "start_offset",
            "end_offset",
            "tags",
            "created_at",
        )
        read_only_fields = ("id", "created_at", "page")

    def create(self, validated_data):
        user = self.context["request"].user
        book = validated_data["book"]
        if book.owner_id != user.id:
            raise serializers.ValidationError({"book": "Invalid book."})
        page_number = validated_data["page_number"]
        page = Page.objects.get(book=book, number=page_number)
        validated_data["page"] = page
        if not validated_data.get("chapter"):
            validated_data["chapter"] = page.chapter
        return Highlight.objects.create(user=user, **validated_data)


class NoteSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)
    chapter_title = serializers.CharField(source="chapter.title", read_only=True)

    class Meta:
        model = Note
        fields = (
            "id",
            "book",
            "book_title",
            "chapter",
            "chapter_title",
            "page",
            "page_number",
            "selected_text",
            "body",
            "tags",
            "highlight",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "page")

    def create(self, validated_data):
        user = self.context["request"].user
        book = validated_data["book"]
        if book.owner_id != user.id:
            raise serializers.ValidationError({"book": "Invalid book."})
        page_number = validated_data["page_number"]
        page = Page.objects.get(book=book, number=page_number)
        validated_data["page"] = page
        if not validated_data.get("chapter"):
            validated_data["chapter"] = page.chapter
        return Note.objects.create(user=user, **validated_data)


class BookmarkSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)

    class Meta:
        model = Bookmark
        fields = (
            "id",
            "book",
            "book_title",
            "page",
            "page_number",
            "label",
            "color",
            "note",
            "created_at",
        )
        read_only_fields = ("id", "created_at", "page")

    def create(self, validated_data):
        user = self.context["request"].user
        book = validated_data["book"]
        page_number = validated_data["page_number"]
        page = Page.objects.get(book=book, number=page_number)
        validated_data["page"] = page
        bookmark, _ = Bookmark.objects.update_or_create(
            user=user,
            book=book,
            page_number=page_number,
            defaults={**validated_data, "page": page},
        )
        return bookmark
