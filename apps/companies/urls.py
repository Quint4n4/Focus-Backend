from django.urls import path

from .views import CompanyMeView, CompanyRegisterView

urlpatterns = [
    path('register/', CompanyRegisterView.as_view(), name='company-register'),
    path('me/',       CompanyMeView.as_view(),        name='company-me'),
]
