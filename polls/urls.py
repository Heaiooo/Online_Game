from django.urls import path
from . import views

urlpatterns = [
    path('', views.start, name='start'),
    path('profile/', views.profile, name='profile'),
    path('session/', views.session, name='session'),
    path('lobby/<str:game_id>/', views.lobby, name='lobby'),
    path('entrance/', views.entrance, name='entrance'),
    path('logout/', views.logout_view, name='logout'),
    path('game/<str:game_id>/', views.game_view, name='game'),
]