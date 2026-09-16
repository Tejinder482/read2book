from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BookViewSet

router = DefaultRouter()
router.register("books", BookViewSet, basename="books")

urlpatterns = [
    path("", include(router.urls)),
]
