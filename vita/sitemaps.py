from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Blog, PrimaryCategory


class PostsSitemap(Sitemap):

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


class PagesSitemap(Sitemap):

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


class CategoriesSitemap(Sitemap):

    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return PrimaryCategory.objects.all()

    def location(self, obj):

        return f'/resources/{obj.slug}/'


class CalculatorsSitemap(Sitemap):

    changefreq = "monthly"
    priority = 0.8

    def items(self):

        return [
            '/calculators/sip',
            '/calculators/emi',
            '/calculators/home-loan',
            '/calculators/car-loan',
            '/calculators/personal-loan',
            '/calculators/ppf',
            '/calculators/nps',
            '/calculators/pf',
            '/calculators/salary',
            '/calculators/retirement',
            '/calculators/loan-eligibility',
        ]

    def location(self, item):
        return item