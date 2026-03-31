from django.urls import path
from . import views

urlpatterns = [
    path('personal/', views.PersonalStatsView.as_view(), name='stats-personal'),
    path('area/<uuid:area_pk>/', views.AreaStatsView.as_view(), name='stats-area'),
    path('drilldown/', views.DrilldownView.as_view(), name='stats-drilldown'),
]
