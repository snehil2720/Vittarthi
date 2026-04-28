from .models import PrimaryCategory

def global_categories(request):
    return {
        'primary_categories': PrimaryCategory.objects.all()
    }