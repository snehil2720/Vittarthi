from django.db import models
from django.contrib.auth.models import User
from ckeditor.fields import RichTextField   
from ckeditor_uploader.fields import RichTextUploadingField
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils.text import slugify
import re
from django.utils.html import strip_tags
import uuid
# class Category(models.Model):
#     name = models.CharField(max_length=100, unique=True)
#     slug = models.SlugField(max_length=100, unique=True, blank=True, null=True)

#     def __str__(self):
#         return self.name
class PrimaryCategory(models.Model):
    name = models.CharField(max_length=250, unique=True)  # Blogs, Case Study, News
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class SecondaryCategory(models.Model):
    name = models.CharField(max_length=250)
    slug = models.SlugField(blank=True, null=True)

    primary = models.ForeignKey(
        PrimaryCategory,
        on_delete=models.CASCADE,
        related_name='secondary_categories'
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
class Blog(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
    )

    title = models.CharField(max_length=250)
    content = RichTextUploadingField()
    image = models.ImageField(upload_to='blogs/', default='default.jpg')
    #category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='blogs')
    primary_category = models.ForeignKey(
        PrimaryCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    secondary_category = models.ForeignKey(
        SecondaryCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    slug = models.SlugField(max_length=250,unique=True, blank=True)
    is_featured = models.BooleanField(default=False, help_text="Check this to show at the top")
    summary = models.TextField(blank=True)
    meta_title = models.CharField(max_length=250, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)
    focus_keyword = models.CharField(max_length=250, blank=True, null=True)

    seo_score = models.IntegerField(default=0)  
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title) 
        if self.is_featured:
            Blog.objects.filter(is_featured=True).exclude(id=self.id).update(is_featured=False)
        self.summary = generate_clean_summary(self.content)
        if not self.meta_title:
            self.meta_title = self.title[:250]
        if not self.meta_description:
            self.meta_description = self.summary[:160]
        super().save(*args, **kwargs)

    #author = models.ForeignKey(User, on_delete=models.CASCADE)
    #author = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    content = RichTextUploadingField()
    likes = models.IntegerField(default=0)
 
    def __str__(self):
        return self.title

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('writer', 'Writer'),
        ('user', 'User'),
    )

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')

    def __str__(self):
        return self.username


class CalcUsage(models.Model):
    name = models.CharField(max_length=100) 
    created_at = models.DateTimeField(auto_now_add=True)

def generate_clean_summary(content):
    if not content:
        return ""

    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'\{[\s\S]*?\}', '', content)

    content = strip_tags(content)
    content = re.sub(r'\s+', ' ', content).strip()

    return " ".join(content.split()[:30]) + "..."

class ContactMessage(models.Model):

    CATEGORY_CHOICES = [
        ('general', 'General Query'),
        ('bug', 'Bug / Error Report'),
        ('content', 'Content Feedback'),
        ('feature', 'Feature Request'),
        ('partnership', 'Partnership'),
        ('privacy', 'Privacy / Legal'),
    ]

    STATUS_CHOICES = [
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('spam', 'Spam'),
    ]

    first_name = models.CharField(max_length=100)

    last_name = models.CharField(
        max_length=100,
        blank=True
    )
    ticket_id = models.CharField(
        max_length=20,
        unique=True,
        blank=True
    )
    email = models.EmailField()

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default='general'
    )

    calculator = models.CharField(
        max_length=150,
        blank=True
    )

    subject = models.CharField(max_length=255)

    message = models.TextField()

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )

    user_agent = models.TextField(
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )
    def save(self, *args, **kwargs):
        if not self.ticket_id:
            self.ticket_id = (
                'VT-' +
                str(uuid.uuid4()).split('-')[0].upper()
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.subject} - {self.email}"


class PrivacyPolicy(models.Model):
    title = models.CharField(max_length=200, default="Privacy Policy")
    content = RichTextUploadingField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
class LegalPage(models.Model):
    PAGE_CHOICES = (
        ('privacy-policy', 'Privacy Policy'),
        ('disclaimer', 'Disclaimer'),
        ('terms-of-use', 'Terms of Use'),
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    page_type = models.CharField(
        max_length=50,
        choices=PAGE_CHOICES,
        unique=True
    )
    short_description = models.TextField(
        max_length=300,
        blank=True,
        null=True
    )
    content = RichTextUploadingField()
    updated_at = models.DateTimeField(auto_now=True)
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    def __str__(self):
        return self.title