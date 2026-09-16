from django.contrib import admin

from .models import Bookmark, Highlight, Note, ReadingProgress

admin.site.register(ReadingProgress)
admin.site.register(Highlight)
admin.site.register(Note)
admin.site.register(Bookmark)
