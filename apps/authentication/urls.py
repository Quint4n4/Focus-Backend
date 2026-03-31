from django.urls import path

from .views import (
    LoginView,
    LogoutView,
    RefreshView,
    MeView,
    BiometricEnableView,
    BiometricDisableView,
    BiometricLoginView,
    OnboardingCompleteView,
)

urlpatterns = [
    path('login/',                    LoginView.as_view(),            name='auth-login'),
    path('logout/',                   LogoutView.as_view(),           name='auth-logout'),
    path('refresh/',                  RefreshView.as_view(),          name='auth-refresh'),
    path('me/',                       MeView.as_view(),               name='auth-me'),
    path('biometric/enable/',         BiometricEnableView.as_view(),  name='biometric-enable'),
    path('biometric/disable/',        BiometricDisableView.as_view(), name='biometric-disable'),
    path('biometric/login/',          BiometricLoginView.as_view(),   name='biometric-login'),
    path('onboarding/complete/',      OnboardingCompleteView.as_view(),name='onboarding-complete'),
]
