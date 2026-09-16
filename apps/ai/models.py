from django.db import models

from apps.accounts.models import User
from apps.library.models import Book


class AIConversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ai_conversations")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="ai_conversations")
    title = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]


class AIMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"

    conversation = models.ForeignKey(
        AIConversation, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    page_number = models.PositiveIntegerField(null=True, blank=True)
    selected_text = models.TextField(blank=True, default="")
    provider = models.CharField(max_length=40, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
