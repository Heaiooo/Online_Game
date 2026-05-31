from django.http import Http404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, ProfileSerializer, \
    GameStatusSerializer
from django.contrib.auth import authenticate
from .models import Profile, Game, Card, ChatMessage
from .serializers import GameCreateSerializer, GameJoinSerializer
from .models import PlayerGame


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()

        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'token': token.key,
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'message': 'Регистрация успешна!'
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)

    if serializer.is_valid():
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        user = authenticate(username=username, password=password)

        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'message': 'Вход выполнен успешно!'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Неверное имя пользователя или пароль'
            }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_stats(request):
    try:
        profile = request.user.profile
        serializer = ProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Profile.DoesNotExist:
        return Response(
            {'error': 'Профиль не найден'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_game(request):
    serializer = GameCreateSerializer(data=request.data)

    if serializer.is_valid():
        game = serializer.save()

        PlayerGame.objects.create(
            user=request.user,
            game=game,
            team='blue',
            role='disassociator',
            score=0
        )

        return Response({
            'game_id': game.game_id,
            'status': game.status,
            'created_at': game.created_at,
            'message': f'Игра {game.game_id} создана!'
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_game(request):
    serializer = GameJoinSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    game_id = serializer.validated_data['game_id']
    game = Game.objects.get(game_id=game_id)

    if PlayerGame.objects.filter(user=request.user, game=game).exists():
        return Response({
            'error': 'Вы уже присоединились к этой игре'
        }, status=status.HTTP_400_BAD_REQUEST)

    blue_count = PlayerGame.objects.filter(game=game, team='blue').count()
    red_count = PlayerGame.objects.filter(game=game, team='red').count()

    if blue_count + red_count == 8:
        return Response({
            'error': 'В данной игре нет места для вас, увы! =('
        }, status=status.HTTP_400_BAD_REQUEST)
    elif blue_count <= red_count:
        team = 'blue'
    else:
        team = 'red'

    PlayerGame.objects.create(
        user=request.user,
        game=game,
        team=team,
        role='disassociator',
        score=0
    )

    return Response({
        'game_id': game.game_id,
        'status': game.status,
        'team': team,
        'message': f'Вы присоединились к игре {game.game_id}!'
    }, status=status.HTTP_200_OK)


def get_game_or_404(game_id):
    try:
        return Game.objects.get(game_id=game_id)
    except Game.DoesNotExist:
        raise Http404


def get_player_or_403(user, game):
    try:
        return PlayerGame.objects.get(user=user, game=game)
    except PlayerGame.DoesNotExist:
        return Response({'error': 'Вы не участвуете в этой игре'}, status=403)


def get_team_scores(game):
    from django.db import models
    blue = PlayerGame.objects.filter(game=game, team='blue').aggregate(total=models.Sum('score'))['total'] or 0
    red = PlayerGame.objects.filter(game=game, team='red').aggregate(total=models.Sum('score'))['total'] or 0
    return {'blue': blue, 'red': red}


def update_users_stats(game):
    winner_team = game.winner_team
    for player in game.playergame_set.all():
        profile = player.user.profile
        profile.games_played += 1
        if player.team == winner_team:
            profile.games_won += 1
        profile.save()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def game_board(request, game_id):
    """Получить карточки для игры с учётом роли"""
    game = get_game_or_404(game_id)
    player = get_player_or_403(request.user, game)

    cards = Card.objects.filter(game=game).order_by('order_position')

    cards_data = []
    for card in cards:
        cards_data.append({
            'id': card.id,
            'word': card.word,
            'is_flipped': card.is_flipped,
            'color': card.color if player.role == 'associator' else None,
            'order_position': card.order_position
        })

    return Response(cards_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def game_status(request, game_id):
    try:
        game = Game.objects.get(game_id=game_id)
    except Game.DoesNotExist:
        return Response({'error': f'Игра {game_id} не найдена'}, status=404)

    try:
        PlayerGame.objects.get(user=request.user, game=game)
    except PlayerGame.DoesNotExist:
        return Response({'error': 'Вы не участвуете в этой игре'}, status=403)

    serializer = GameStatusSerializer(game)
    return Response(serializer.data)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def game_chat(request, game_id):
    game = get_game_or_404(game_id)
    player = get_player_or_403(request.user, game)

    if request.method == 'GET':
        messages = ChatMessage.objects.filter(
            game=game,
            team=player.team
        ).order_by('created_at')[:50]

        data = [{
            'username': msg.user.username if msg.user else 'Система',
            'message': msg.message,
            'created_at': msg.created_at
        } for msg in messages]

        return Response(data)

    elif request.method == 'POST':
        if game.status != 'active':
            return Response({'error': 'Игра не активна'}, status=400)

        if player.role == 'disassociator':
            return Response({'error': 'Десоциаторы могут только читать чат команды'}, status=403)

        if game.current_turn_team != player.team:
            return Response({'error': 'Сейчас ход другой команды'}, status=400)

        if game.turn_phase != 'hint':
            return Response({'error': 'Вы уже дали подсказку, ожидайте хода десоциаторов'}, status=400)

        message_text = request.data.get('message')
        if not message_text:
            return Response({'error': 'Сообщение не может быть пустым'}, status=400)

        formatted_message = f"Подсказка: {message_text}"

        ChatMessage.objects.create(
            game=game,
            user=request.user,
            team=player.team,
            message=formatted_message
        )

        game.current_turn_word = message_text
        game.turn_phase = 'guess'
        game.save()

        return Response({
            'success': True,
            'message': 'Подсказка принята, ход передан десоциаторам вашей команды.'
        })
