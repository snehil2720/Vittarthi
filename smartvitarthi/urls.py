from django.urls import path
from .views import advisor_api,advisor_page,chat_api

urlpatterns = [
    path('api/', advisor_api),
    path('', advisor_page), 
    path('chat/abc', chat_api),
]