from django.urls import path

from .views import BookChatView, BookConversationView, BookExplainView

urlpatterns = [
    path("books/<int:book_id>/ai/explain/", BookExplainView.as_view(), name="ai-explain"),
    path("books/<int:book_id>/ai/chat/", BookChatView.as_view(), name="ai-chat"),
    path(
        "books/<int:book_id>/ai/conversation/",
        BookConversationView.as_view(),
        name="ai-conversation",
    ),
]
