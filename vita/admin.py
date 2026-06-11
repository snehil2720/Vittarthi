from django.contrib import admin
from .models import Blog,PrimaryCategory,SecondaryCategory,ContactMessage,PrivacyPolicy,LegalPage,Author,CustomUser
from django.contrib.auth.admin import UserAdmin
admin.site.register(SecondaryCategory)
admin.site.register(PrimaryCategory)
admin.site.register(PrivacyPolicy)
admin.site.register(LegalPage)
admin.site.register(Author)
@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'is_featured', 'created_at')
    list_editable = ('is_featured',)

admin.site.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):

    list_display = (
        'first_name',
        'email',
        'category',
        'status',
        'created_at'
    )

    list_filter = (
        'category',
        'status',
        'created_at'
    )

    search_fields = (
        'first_name',
        'email',
        'subject'
    )

    readonly_fields = (
        'ip_address',
        'user_agent',
        'created_at'
    )
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):

    list_display = (
        'username',
        'email',
        'role',
        'is_staff',
        'is_active',
    )

    fieldsets = UserAdmin.fieldsets + (
        (
            'Role Management',
            {
                'fields': ('role',)
            }
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            'Role Management',
            {
                'fields': ('role',)
            }
        ),
    )