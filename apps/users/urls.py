from django.urls import path
from . import views

urlpatterns = [
    path('', views.UserListView.as_view(), name='user-list'),
    path('<uuid:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    path('invite/', views.InviteView.as_view(), name='user-invite'),
    path('invite/verify/', views.VerifyInviteView.as_view(), name='invite-verify'),
    path('accept-invite/', views.AcceptInviteView.as_view(), name='accept-invite'),
]
