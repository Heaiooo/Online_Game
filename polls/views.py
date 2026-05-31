from django.shortcuts import render, redirect
from django.contrib.auth import logout


def start(request):
    return render(request, 'polls/start.html')


def profile(request):
    return render(request, 'polls/profile.html')


def session(request):
    return render(request, 'polls/session.html')


def entrance(request):
    return render(request, 'polls/entrance.html')


def lobby(request, game_id):
    return render(request, 'polls/lobby.html', {'game_id': game_id})


def logout_view(request):
    logout(request)
    return redirect('/polls/entrance/')


def game_view(request, game_id):
    return render(request, 'polls/game.html', {'game_id': game_id})
