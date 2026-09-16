from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import AIProviderKey
from apps.common.crypto import decrypt_value
from apps.library.models import Book, Page

from .models import AIConversation, AIMessage
from .providers import ProviderError, get_provider
from .serializers import (
    AIConversationSerializer,
    AIMessageSerializer,
    ChatSerializer,
    ExplainSerializer,
)


def _resolve_key(user, provider_name: str | None):
    preferred = provider_name or getattr(user.profile, "preferred_ai_provider", "") or ""
    qs = AIProviderKey.objects.filter(user=user, is_active=True)
    key = None
    if preferred:
        key = qs.filter(provider=preferred).first()
    if not key:
        key = qs.first()
    if not key:
        raise ProviderError(
            "No AI API key configured. Add your OpenAI, Gemini, or Anthropic key in Settings.",
            code="missing_api_key",
        )
    return key.provider, decrypt_value(key.encrypted_key)


def _page_context(book: Book, page_number: int | None, selected: str = "") -> str:
    parts = [f"Book: {book.title}"]
    if page_number:
        page = Page.objects.filter(book=book, number=page_number).first()
        if page:
            parts.append(f"Page {page_number}:\n{page.text[:3000]}")
            if page.chapter:
                parts.append(f"Chapter: {page.chapter.title}")
    if selected:
        parts.append(f"Selected text:\n{selected}")
    return "\n\n".join(parts)


class BookExplainView(APIView):
    def post(self, request, book_id):
        try:
            book = Book.objects.get(pk=book_id, owner=request.user)
        except Book.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        ser = ExplainSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        try:
            provider_name, api_key = _resolve_key(request.user, data.get("provider"))
            provider = get_provider(provider_name, api_key)
            context = _page_context(book, data.get("page_number"), data["text"])
            answer = provider.explain(data["text"], data.get("style") or "balanced", context)
        except ProviderError as exc:
            code = status.HTTP_400_BAD_REQUEST if exc.code == "missing_api_key" else 502
            return Response(
                {"error": True, "detail": str(exc), "code": exc.code},
                status=code,
            )
        return Response(
            {
                "provider": provider_name,
                "explanation": answer,
                "selected_text": data["text"],
                "style": data.get("style") or "balanced",
            }
        )


class BookChatView(APIView):
    def post(self, request, book_id):
        try:
            book = Book.objects.get(pk=book_id, owner=request.user)
        except Book.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        ser = ChatSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        conversation_id = data.get("conversation_id")
        if conversation_id:
            conversation = AIConversation.objects.filter(
                id=conversation_id, user=request.user, book=book
            ).first()
            if not conversation:
                return Response({"detail": "Conversation not found."}, status=404)
        else:
            conversation = AIConversation.objects.create(
                user=request.user,
                book=book,
                title=(data["message"][:80] or "Chat"),
            )

        AIMessage.objects.create(
            conversation=conversation,
            role=AIMessage.Role.USER,
            content=data["message"],
            page_number=data.get("page_number"),
            selected_text=data.get("selected_text") or "",
        )

        history = [
            {"role": m.role, "content": m.content}
            for m in conversation.messages.exclude(role=AIMessage.Role.SYSTEM)
        ]

        try:
            provider_name, api_key = _resolve_key(request.user, data.get("provider"))
            provider = get_provider(provider_name, api_key)
            context = _page_context(
                book, data.get("page_number"), data.get("selected_text") or ""
            )
            answer = provider.chat(history, context=context)
        except ProviderError as exc:
            code = status.HTTP_400_BAD_REQUEST if exc.code == "missing_api_key" else 502
            return Response(
                {"error": True, "detail": str(exc), "code": exc.code},
                status=code,
            )

        assistant = AIMessage.objects.create(
            conversation=conversation,
            role=AIMessage.Role.ASSISTANT,
            content=answer,
            page_number=data.get("page_number"),
            provider=provider_name,
        )
        conversation.save(update_fields=["updated_at"])
        return Response(
            {
                "conversation_id": conversation.id,
                "provider": provider_name,
                "message": AIMessageSerializer(assistant).data,
            }
        )


class BookConversationView(APIView):
    def get(self, request, book_id):
        conversation = (
            AIConversation.objects.filter(user=request.user, book_id=book_id)
            .prefetch_related("messages")
            .first()
        )
        if not conversation:
            return Response({"id": None, "messages": []})
        return Response(AIConversationSerializer(conversation).data)
