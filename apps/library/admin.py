from django.contrib import admin

from .models import Book, Chapter, Page, ProcessingJob


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "status", "page_count", "updated_at")
    list_filter = ("status",)
    search_fields = ("title", "owner__email")


admin.site.register(Chapter)
admin.site.register(Page)
admin.site.register(ProcessingJob)
