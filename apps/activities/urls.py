from django.urls import path
from . import views

urlpatterns = [
    path('', views.ActivityListCreateView.as_view(), name='activity-list-create'),
    path('<uuid:pk>/', views.ActivityDetailView.as_view(), name='activity-detail'),
    path('<uuid:pk>/move/', views.MoveActivityView.as_view(), name='activity-move'),
    path('<uuid:pk>/assign/', views.AssignActivityView.as_view(), name='activity-assign'),
    path('<uuid:pk>/complete/', views.CompleteActivityView.as_view(), name='activity-complete'),
    path('<uuid:pk>/attachments/', views.AttachmentListCreateView.as_view(), name='activity-attachments'),
    path('<uuid:pk>/attachments/<uuid:attachment_pk>/file/', views.ServeAttachmentFileView.as_view(), name='attachment-file'),
    path('<uuid:pk>/attachments/<uuid:attachment_pk>/', views.AttachmentDeleteView.as_view(), name='attachment-delete'),
    path('<uuid:pk>/logs/', views.ActivityLogListView.as_view(), name='activity-logs'),
]
