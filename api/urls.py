from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('profile/', views.profile, name='profile'),
    path('profile/stats/', views.profile_stats, name='profile_stats'),
    path('game/create/', views.create_game, name='create_game'),
    path('game/join/', views.join_game, name='join_game'),
    path('game/board/<str:game_id>/', views.game_board, name='game_board'),
    path('game/status/<str:game_id>/', views.game_status, name='game_status'),
    path('game/chat/<str:game_id>/', views.game_chat, name='game_chat'),
]

urlpatterns = format_suffix_patterns(urlpatterns)