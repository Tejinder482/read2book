from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.common.crypto import encrypt_value, last4

from .models import AIProviderKey, Profile

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ("id", "email", "password", "first_name")

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = (
            "onboarding_completed",
            "use_cases",
            "help_goals",
            "font_size",
            "line_spacing",
            "theme",
            "font_family",
            "reading_width",
            "preferred_ai_provider",
            "explanation_level",
            "preferred_language",
        )


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "display_name",
            "profile",
            "date_joined",
        )
        read_only_fields = ("email", "date_joined")


class UserUpdateSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(required=False)

    class Meta:
        model = User
        fields = ("first_name", "last_name", "profile")

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if profile_data is not None:
            profile = instance.profile
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
        return instance


class OnboardingSerializer(serializers.Serializer):
    use_cases = serializers.ListField(
        child=serializers.CharField(max_length=60), required=False, default=list
    )
    help_goals = serializers.ListField(
        child=serializers.CharField(max_length=80), required=False, default=list
    )
    font_size = serializers.IntegerField(required=False, min_value=12, max_value=32)
    line_spacing = serializers.ChoiceField(
        choices=Profile.LineSpacing.choices, required=False
    )
    theme = serializers.ChoiceField(choices=Profile.Theme.choices, required=False)
    complete = serializers.BooleanField(default=False)

    def save(self, **kwargs):
        user = self.context["request"].user
        profile = user.profile
        data = self.validated_data
        if "use_cases" in data:
            profile.use_cases = data["use_cases"]
        if "help_goals" in data:
            profile.help_goals = data["help_goals"]
        if "font_size" in data:
            profile.font_size = data["font_size"]
        if "line_spacing" in data:
            profile.line_spacing = data["line_spacing"]
        if "theme" in data:
            profile.theme = data["theme"]
        if data.get("complete"):
            profile.onboarding_completed = True
        profile.save()
        return profile


class AIProviderKeySerializer(serializers.ModelSerializer):
    api_key = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = AIProviderKey
        fields = (
            "id",
            "provider",
            "label",
            "api_key",
            "key_last4",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("key_last4", "created_at", "updated_at")

    def create(self, validated_data):
        raw = validated_data.pop("api_key")
        validated_data["encrypted_key"] = encrypt_value(raw)
        validated_data["key_last4"] = last4(raw)
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        raw = validated_data.pop("api_key", None)
        if raw:
            instance.encrypted_key = encrypt_value(raw)
            instance.key_last4 = last4(raw)
        return super().update(instance, validated_data)


class GoogleLoginSerializer(serializers.Serializer):
    """Accepts an ID token from Google Identity Services (frontend)."""

    id_token = serializers.CharField()
