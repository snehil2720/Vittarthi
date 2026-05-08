"""
URL configuration for vitarthi project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from ckeditor_uploader import views as ckeditor_views
from django.contrib.sitemaps.views import sitemap
from vita.sitemaps import StaticViewSitemap, BlogSitemap
#from django.views.generic import TemplateView
sitemaps = {
    'static': StaticViewSitemap,
    'blogs': BlogSitemap,
}
urlpatterns = [
    path('admin/', admin.site.urls),
    path('',include('vita.urls')),  
    #path('ckeditor/', include('ckeditor_uploader.urls')),
    path('ckeditor/upload/', ckeditor_views.upload, name='ckeditor_upload'),
    path('ckeditor/browse/', ckeditor_views.browse, name='ckeditor_browse'),
    path('smart/', include('smartvitarthi.urls')),
    path(
    'sitemap.xml',
    sitemap,
    {'sitemaps': sitemaps},
    name='django.contrib.sitemaps.views.sitemap'
    )
    # path(
    # "robots.txt",
    # TemplateView.as_view(
    #     template_name="robots.txt",
    #     content_type="text/plain"
    # ),
    # ),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
handler404 = 'vita.views.custom_404'
handler500 = 'vita.views.custom_500'
handler403 = 'vita.views.custom_403'
handler400 = 'vita.views.custom_400'
