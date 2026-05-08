from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Blog


class StaticViewSitemap(Sitemap):

    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return [
            'home',
            'calculators',
            'contact',
        ]

    def location(self, item):
        return reverse(item)


class BlogSitemap(Sitemap):

    changefreq = "daily"
    priority = 0.9

    def items(self):
        return Blog.objects.filter(status='published')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):

        primary_slug = "blogs"

        if obj.primary_category:
            primary_slug = obj.primary_category.slug

        return f'/resources/{primary_slug}/{obj.slug}/'