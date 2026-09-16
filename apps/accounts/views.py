from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .jwt_serializers import EmailTokenObtainPairSerializer
from .models import AIProviderKey
from .serializers import (
    AIProviderKeySerializer,
    GoogleLoginSerializer,
    OnboardingSerializer,
    ProfileSerializer,
    RegisterSerializer,
    UserSerializer,
    UserUpdateSerializer,
)

User = get_user_model()


def tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user": UserSerializer(user).data,
    }


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(tokens_for_user(user), status=status.HTTP_201_CREATED)


class EmailTokenObtainPairView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]
    serializer_class = EmailTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.user
        return Response(
            {
                **serializer.validated_data,
                "user": UserSerializer(user).data,
            }
        )


class MeView(generics.RetrieveUpdateAPIView):
    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return UserUpdateSerializer
        return UserSerializer

    def get_object(self):
        return self.request.user


class OnboardingView(APIView):
    def post(self, request):
        serializer = OnboardingSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        return Response(ProfileSerializer(profile).data)


class AIProviderKeyViewSet(viewsets.ModelViewSet):
    serializer_class = AIProviderKeySerializer

    def get_queryset(self):
        return AIProviderKey.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save()


class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["id_token"]
        client_id = settings.SOCIALACCOUNT_PROVIDERS["google"]["APP"]["client_id"]
        if not client_id:
            return Response(
                {
                    "error": True,
                    "detail": "Google OAuth is not configured. Set GOOGLE_CLIENT_ID.",
                    "code": "google_not_configured",
                },
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )
        try:
            from google.oauth2 import id_token as google_id_token
            from google.auth.transport import requests as google_requests

            info = google_id_token.verify_oauth2_token(
                token, google_requests.Request(), client_id
            )
        except Exception:
            return Response(
                {"error": True, "detail": "Invalid Google token.", "code": "invalid_token"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        email = info.get("email")
        if not email:
            return Response(
                {"error": True, "detail": "Email missing from Google token.", "code": "no_email"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": info.get("given_name", ""),
                "last_name": info.get("family_name", ""),
            },
        )
        if created:
            user.set_unusable_password()
            user.save()
        return Response(tokens_for_user(user))


class HealthView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"status": "ok", "service": "ai-book-reader"})
