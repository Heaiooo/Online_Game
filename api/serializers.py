from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import Profile
import random
import string
from .models import Game, PlayerGame


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True
    )
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'password2', 'email']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {"password": "Пароли не совпадают"}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class ProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    games_played = serializers.IntegerField(read_only=True)
    games_won = serializers.IntegerField(read_only=True)
    winrate = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['user_id', 'username', 'email', 'games_played', 'games_won', 'winrate']

    def get_winrate(self, obj):
        return obj.winrate


class GameCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = ['game_id', 'status', 'created_at']
        read_only_fields = ['game_id', 'status', 'created_at']

    def create(self, validated_data):
        game_id = self.generate_unique_game_id()
        game = Game.objects.create(
            game_id=game_id,
            status='waiting',
            **validated_data
        )
        return game

    def generate_unique_game_id(self):
        while True:
            game_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            print(game_id)
            if not Game.objects.filter(game_id=game_id).exists():
                return game_id


class GameJoinSerializer(serializers.Serializer):
    game_id = serializers.CharField(max_length=10, required=True)

    def validate_game_id(self, value):

        if not Game.objects.filter(game_id=value).exists():
            raise serializers.ValidationError(f"Игра с кодом {value} не найдена")

        game = Game.objects.get(game_id=value)

        if game.status != 'waiting':
            raise serializers.ValidationError(f"Игра уже {game.status}")

        return value


class GameStatusSerializer(serializers.ModelSerializer):
    blue_team = serializers.SerializerMethodField()
    red_team = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = ['game_id',
                  'status',
                  'blue_team',
                  'red_team',
                  'current_turn_team',
                  'turn_phase',
                  'winner_team',
                  'blue_score',
                  'red_score'
                  ]

    def get_blue_team(self, obj):
        players = obj.playergame_set.filter(team='blue')
        return PlayerGameDetailSerializer(players, many=True).data

    def get_red_team(self, obj):
        players = obj.playergame_set.filter(team='red')
        return PlayerGameDetailSerializer(players, many=True).data


class PlayerGameDetailSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = PlayerGame
        fields = ['username', 'team', 'role', 'score']
