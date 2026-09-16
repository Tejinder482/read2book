from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AIProviderKeyViewSet, MeView, OnboardingView

router = DefaultRouter()
router.register("ai-keys", AIProviderKeyViewSet, basename="ai-keys")

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("onboarding/", OnboardingView.as_view(), name="onboarding"),
    path("", include(router.urls)),
]
