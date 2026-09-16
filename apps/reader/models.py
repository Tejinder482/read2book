from django.db import models

from apps.accounts.models import User
from apps.library.models import Book, Chapter, Page


class ReadingProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="progress")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="progress")
    current_page = models.PositiveIntegerField(default=1)
    current_chapter = models.ForeignKey(
        Chapter, on_delete=models.SET_NULL, null=True, blank=True
    )
    reading_seconds = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "book")

    def __str__(self):
        return f"{self.user_id}/{self.book_id} @ {self.current_page}"


class Highlight(models.Model):
    class Color(models.TextChoices):
        YELLOW = "yellow", "Yellow"
        GREEN = "green", "Green"
        BLUE = "blue", "Blue"
        PURPLE = "purple", "Purple"
        RED = "red", "Red"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="highlights")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="highlights")
    chapter = models.ForeignKey(
        Chapter, on_delete=models.SET_NULL, null=True, blank=True
    )
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="highlights")
    page_number = models.PositiveIntegerField()
    selected_text = models.TextField()
    color = models.CharField(max_length=20, choices=Color.choices, default=Color.YELLOW)
    start_offset = models.PositiveIntegerField(default=0)
    end_offset = models.PositiveIntegerField(default=0)
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Note(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notes")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="notes")
    chapter = models.ForeignKey(
        Chapter, on_delete=models.SET_NULL, null=True, blank=True
    )
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="notes")
    page_number = models.PositiveIntegerField()
    selected_text = models.TextField(blank=True, default="")
    body = models.TextField()
    tags = models.JSONField(default=list, blank=True)
    highlight = models.ForeignKey(
        Highlight,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]


class Bookmark(models.Model):
    class Color(models.TextChoices):
        RED = "red", "Red"
        YELLOW = "yellow", "Yellow"
        BLUE = "blue", "Blue"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookmarks")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="bookmarks")
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="bookmarks")
    page_number = models.PositiveIntegerField()
    label = models.CharField(max_length=120, blank=True, default="")
    color = models.CharField(max_length=20, choices=Color.choices, default=Color.RED)
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("user", "book", "page_number")
