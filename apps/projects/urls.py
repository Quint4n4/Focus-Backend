from django.urls import path
from . import views

urlpatterns = [
    path('', views.ProjectListCreateView.as_view(), name='project-list-create'),
    path('<uuid:pk>/', views.ProjectDetailView.as_view(), name='project-detail'),
    path('<uuid:pk>/activities/', views.ProjectActivitiesView.as_view(), name='project-activities'),
    path('<uuid:pk>/progress/', views.ProjectProgressView.as_view(), name='project-progress'),
]
