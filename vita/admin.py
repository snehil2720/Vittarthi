from django.contrib import admin
from .models import Blog, Category

admin.site.register(Category)
# admin.site.register(Blog)

@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'is_featured', 'created_at')
    list_editable = ('is_featured',)