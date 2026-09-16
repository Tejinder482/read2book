from django.conf import settings
from django.db import models

from apps.accounts.models import User


class Book(models.Model):
    class Status(models.TextChoices):
        UPLOADING = "uploading", "Uploading"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="books")
    title = models.CharField(max_length=255, blank=True, default="")
    author = models.CharField(max_length=255, blank=True, default="")
    file = models.FileField(upload_to="books/%Y/%m/")
    cover = models.ImageField(upload_to="covers/%Y/%m/", blank=True, null=True)
    page_count = models.PositiveIntegerField(default=0)
    chapter_count = models.PositiveIntegerField(default=0)
    file_size = models.PositiveBigIntegerField(default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.UPLOADING
    )
    overview = models.TextField(blank=True, default="")
    estimated_reading_hours = models.FloatField(default=0)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_opened_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_opened_at", "-updated_at"]

    def __str__(self):
        return self.title or f"Book #{self.pk}"


class Chapter(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="chapters")
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    start_page = models.PositiveIntegerField(default=1)
    end_page = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order", "start_page"]
        unique_together = ("book", "order")

    def __str__(self):
        return f"{self.book_id}: {self.title}"


class Page(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="pages")
    chapter = models.ForeignKey(
        Chapter, on_delete=models.SET_NULL, null=True, blank=True, related_name="pages"
    )
    number = models.PositiveIntegerField()
    text = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["number"]
        unique_together = ("book", "number")
        indexes = [
            models.Index(fields=["book", "number"]),
        ]

    def __str__(self):
        return f"{self.book_id} p.{self.number}"


class ProcessingJob(models.Model):
    class StepStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    STEPS = (
        ("uploaded", "PDF uploaded"),
        ("extracting", "Extracting text"),
        ("chapters", "Detecting chapters"),
        ("pages", "Processing pages"),
        ("index", "Creating searchable index"),
        ("ai_kb", "Preparing AI knowledge base"),
        ("finalizing", "Finalizing"),
    )

    book = models.OneToOneField(Book, on_delete=models.CASCADE, related_name="processing_job")
    steps = models.JSONField(default=dict)
    requires_ocr = models.BooleanField(default=False)
    ocr_message = models.CharField(max_length=255, blank=True, default="")
    current_step = models.CharField(max_length=40, blank=True, default="")
    progress_percent = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def init_steps(self):
        self.steps = {
            key: {"label": label, "status": self.StepStatus.PENDING}
            for key, label in self.STEPS
        }
        self.save(update_fields=["steps", "updated_at"])

    def set_step(self, key: str, status: str, percent: int | None = None):
        if key not in self.steps:
            return
        self.steps[key]["status"] = status
        self.current_step = key
        if percent is not None:
            self.progress_percent = percent
        self.save(update_fields=["steps", "current_step", "progress_percent", "updated_at"])
