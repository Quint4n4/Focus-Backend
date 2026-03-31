from django.urls import path

from . import views

urlpatterns = [
    path('', views.AreaListCreateView.as_view(), name='area-list-create'),
    path('<uuid:pk>/', views.AreaDetailView.as_view(), name='area-detail'),
    path('<uuid:pk>/members/', views.AreaMembersView.as_view(), name='area-members'),
]
