from rest_framework import serializers

from .models import AIConversation, AIMessage


class AIMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIMessage
        fields = (
            "id",
            "role",
            "content",
            "page_number",
            "selected_text",
            "provider",
            "created_at",
        )


class AIConversationSerializer(serializers.ModelSerializer):
    messages = AIMessageSerializer(many=True, read_only=True)

    class Meta:
        model = AIConversation
        fields = ("id", "book", "title", "messages", "created_at", "updated_at")


class ExplainSerializer(serializers.Serializer):
    text = serializers.CharField()
    style = serializers.ChoiceField(
        choices=["simpler", "technical", "example", "balanced"],
        default="balanced",
        required=False,
    )
    page_number = serializers.IntegerField(required=False, allow_null=True)
    provider = serializers.CharField(required=False, allow_blank=True)


class ChatSerializer(serializers.Serializer):
    message = serializers.CharField()
    page_number = serializers.IntegerField(required=False, allow_null=True)
    selected_text = serializers.CharField(required=False, allow_blank=True, default="")
    provider = serializers.CharField(required=False, allow_blank=True)
    conversation_id = serializers.IntegerField(required=False, allow_null=True)
