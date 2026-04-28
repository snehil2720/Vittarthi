from django.contrib import admin
from .models import Blog,PrimaryCategory,SecondaryCategory

admin.site.register(SecondaryCategory)
admin.site.register(PrimaryCategory)

@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'is_featured', 'created_at')
    list_editable = ('is_featured',)