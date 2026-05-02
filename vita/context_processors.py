from .models import PrimaryCategory,Blog, CalcUsage

def global_categories(request):
    return {
        'primary_categories': PrimaryCategory.objects.all()
    }
from django.utils.timezone import now

def site_stats(request):
    current_month = now().month
    total_blogs = Blog.objects.filter(status='published').count()

    total_calculators = 11  # static ya baad me dynamic kar sakte

    #monthly_users = CalcUsage.objects.count()  # total usage
    monthly_users = CalcUsage.objects.filter(
    created_at__month=current_month
    ).count()

    return {
        'total_blogs': total_blogs,
        'total_calculators': total_calculators,
        'monthly_users': monthly_users
    }