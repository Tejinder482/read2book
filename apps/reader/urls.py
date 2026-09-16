from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BookmarkViewSet, HighlightViewSet, NoteViewSet, ProgressView

router = DefaultRouter()
router.register("highlights", HighlightViewSet, basename="highlights")
router.register("notes", NoteViewSet, basename="notes")
router.register("bookmarks", BookmarkViewSet, basename="bookmarks")

urlpatterns = [
    path("books/<int:book_id>/progress/", ProgressView.as_view(), name="progress"),
    path("", include(router.urls)),
]
