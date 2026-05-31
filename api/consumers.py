import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from rest_framework.authtoken.models import Token
from .models import Game, Card, PlayerGame, ChatMessage


class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.game_id = self.scope['url_route']['kwargs']['game_id']

            token_key = self.get_token_from_scope()
            self.user = await self.get_user_by_token(token_key)
            print(f"User: {self.user}")

            if not self.user:
                print("No user, closing")
                await self.close()
                return

            if not await self.user_in_game(self.user, self.game_id):
                print("User not in game, closing")
                await self.close()
                return

            self.team = await self.get_user_team(self.user, self.game_id)

            self.player_role = await self.get_user_role(self.user, self.game_id)

            if not self.player_role or self.player_role not in ('associator', 'disassociator'):
                print(f"Invalid role '{self.player_role}', closing")
                await self.close()
                return

            self.group_name = f'game_{self.game_id}'
            self.group_name_team = f'game_{self.game_id}_{self.team}'
            self.group_name_role = f'game_{self.game_id}_{self.player_role}'

            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.channel_layer.group_add(self.group_name_team, self.channel_name)
            await self.channel_layer.group_add(self.group_name_role, self.channel_name)

            await self.accept()
            await self.send_game_status()
        except Exception as e:
            print(f"EXCEPTION in connect: {e}")
            import traceback
            traceback.print_exc()
            await self.close()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

        await self.channel_layer.group_discard(
            self.group_name_team,
            self.channel_name
        )

        await self.channel_layer.group_discard(
            self.group_name_role,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'chat_message':
            await self.handle_chat_message(data.get('message'))
        elif message_type == 'guess':
            await self.handle_guess(data.get('card_id'))
        elif message_type == 'end_turn':
            await self.handle_end_turn()

    async def send_game_status(self):
        """Отправляет текущее состояние игры всем в группе"""

        status_associator = await self.get_game_status(self.game_id, 'associator')
        status_disassociator = await self.get_game_status(self.game_id, 'disassociator')

        await self.channel_layer.group_send(
            f'game_{self.game_id}_associator',
            {
                'type': 'game_update',
                'data': status_associator
            }
        )

        await self.channel_layer.group_send(
            f'game_{self.game_id}_disassociator',
            {
                'type': 'game_update',
                'data': status_disassociator
            }
        )

    async def game_update(self, event):
        """Отправляет обновление игры клиенту"""
        await self.send(text_data=json.dumps({
            'type': 'game_update',
            'data': event['data']
        }))

    async def chat_update(self, event):
        """Отправляет новое сообщение чата клиенту"""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'data': event['data']
        }))

    async def handle_chat_message(self, message):
        if not message:
            print("NO MESSAGE")
            return

        can_send = await self.can_send_chat_message(self.user, self.game_id)
        print(f"can_send={can_send}")
        if not can_send:
            return

        print("Creating chat message...")
        chat_message = await self.create_chat_message(self.user, self.game_id, message)
        print(f"Created: {chat_message}")

        await self.channel_layer.group_send(
            self.group_name_team,
            {
                'type': 'chat_update',
                'data': {
                    'username': self.user.username,
                    'message': message,
                    'created_at': str(chat_message.created_at)
                }
            }
        )

        await self.switch_to_guess_phase(self.game_id)
        await self.send_game_status()

    async def handle_guess(self, card_id):
        """Обработка угадывания карточки"""
        can_guess = await self.can_guess_card(self.user, self.game_id)
        if not can_guess:
            return

        result = await self.process_guess(self.user, self.game_id, card_id)

        await self.send_game_status()

        if result.get('game_over'):
            # send_game_status уже отправил полное состояние со статусом 'finished' и winner_team
            pass

    async def handle_end_turn(self):
        await self.switch_to_hint_phase(self.game_id)
        await self.send_game_status()

    def get_token_from_scope(self):
        from urllib.parse import parse_qs
        query_string = self.scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        token_list = params.get('token')
        if token_list:
            return token_list[0]
        return None

    @database_sync_to_async
    def get_user_by_token(self, token_key):
        """Получает пользователя по токену"""
        try:
            token = Token.objects.get(key=token_key)
            return token.user
        except Token.DoesNotExist:
            return None

    @database_sync_to_async
    def user_in_game(self, user, game_id):
        """Проверяет, участвует ли пользователь в игре"""
        try:
            game = Game.objects.get(game_id=game_id)
            return PlayerGame.objects.filter(user=user, game=game).exists()
        except Game.DoesNotExist:
            return False

    @database_sync_to_async
    def get_user_team(self, user, game_id):
        game = Game.objects.get(game_id=game_id)
        player = PlayerGame.objects.get(user=user, game=game)
        return player.team

    @database_sync_to_async
    def get_user_role(self, user, game_id):
        game = Game.objects.get(game_id=game_id)
        player = PlayerGame.objects.get(user=user, game=game)
        return player.role

    @database_sync_to_async
    def get_game_status(self, game_id, player_role):
        from .serializers import GameStatusSerializer
        game = Game.objects.get(game_id=game_id)
        game_data = GameStatusSerializer(game).data

        if player_role == 'associator':
            cards = list(
                Card.objects.filter(game=game)
                .order_by('order_position')
                .values(
                    'id',
                    'word',
                    'color',
                    'is_flipped',
                    'order_position'
                )
            )
        else:
            cards = list(
                Card.objects.filter(game=game)
                .order_by('order_position')
                .values(
                    'id',
                    'word',
                    'is_flipped',
                    'order_position'
                )
            )
        game_data['cards'] = cards
        return game_data

    @database_sync_to_async
    def can_send_chat_message(self, user, game_id):
        """Проверяет, может ли пользователь писать в чат"""
        game = Game.objects.get(game_id=game_id)
        player = PlayerGame.objects.get(user=user, game=game)
        print(f"role={player.role}, phase={game.turn_phase}, turn={game.current_turn_team}, team={player.team}")

        return (player.role == 'associator' and
                game.turn_phase == 'hint' and
                game.current_turn_team == player.team)

    @database_sync_to_async
    def can_guess_card(self, user, game_id):
        """Проверяет, может ли пользователь угадывать"""
        game = Game.objects.get(game_id=game_id)
        player = PlayerGame.objects.get(user=user, game=game)

        # Только десоциатор в фазе guess может угадывать
        return (player.role == 'disassociator' and
                game.turn_phase == 'guess' and
                game.current_turn_team == player.team)

    @database_sync_to_async
    def create_chat_message(self, user, game_id, message):
        """Создаёт сообщение в чате"""
        game = Game.objects.get(game_id=game_id)
        player = PlayerGame.objects.get(user=user, game=game)
        formatted_message = f"Подсказка: {message}"
        return ChatMessage.objects.create(
            game=game,
            user=user,
            team=player.team,
            message=formatted_message
        )

    @database_sync_to_async
    def switch_to_guess_phase(self, game_id):
        """Переключает игру в фазу угадывания"""
        game = Game.objects.get(game_id=game_id)
        game.turn_phase = 'guess'
        game.current_turn_word = None
        game.save()

    @database_sync_to_async
    def switch_to_hint_phase(self, game_id):
        """Переключает игру в фазу угадывания"""
        game = Game.objects.get(game_id=game_id)
        game.current_turn_team = 'red' if game.current_turn_team == 'blue' else 'blue'
        game.turn_phase = 'hint'
        game.current_turn_word = None
        game.save()

    @database_sync_to_async
    def process_guess(self, user, game_id, card_id):
        """Обрабатывает угадывание карточки"""
        from .models import Card

        game = Game.objects.get(game_id=game_id)
        player = PlayerGame.objects.get(user=user, game=game)

        try:
            card = Card.objects.get(id=card_id, game=game)
        except Card.DoesNotExist:
            return {'error': 'Карточка не найдена'}

        if card.is_flipped:
            return {'error': 'Карточка уже открыта'}

        if card.color == player.team:
            result = 'own'
            turn_ends = False
        elif card.color in ('blue', 'red') and card.color != player.team:
            result = 'opponent'
            turn_ends = True
        else:
            result = 'black'
            turn_ends = True

        card.is_flipped = True
        card.flipped_by = user
        card.save()

        if result == 'own':
            if player.team == 'red':
                game.red_score += 1
            else:
                game.blue_score += 1

        elif result == 'opponent':
            if card.color == 'red':
                game.red_score += 1
            else:
                game.blue_score += 1

        elif result == 'black':
            if player.team == 'red':
                game.red_score -= 1
            else:
                game.blue_score -= 1

        game.save()


        player.save()

        # Проверка окончания игры
        team_cards_left = Card.objects.filter(game=game, color=player.team, is_flipped=False).count()
        if team_cards_left == 0:
            game.status = 'finished'
            game.winner_team = player.team
            game.save()
            from .views import update_users_stats
            update_users_stats(game)
            return {'game_over': True, 'winner_team': player.team}

        if turn_ends:
            # Переключаем ход
            game.current_turn_team = 'red' if game.current_turn_team == 'blue' else 'blue'
            game.turn_phase = 'hint'
            game.save()

        return {'success': True, 'result': result}


class LobbyConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.group_name = f'lobby_{self.game_id}'

        token_key = self.get_token_from_scope()
        self.user = await self.get_user_by_token(token_key)

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        await self.send_lobby_status()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type')

        if msg_type == 'lobby':
            await self.send_lobby_status()
        elif msg_type == 'choose_role':
            role = data.get('role')
            await self.choose_role(role)
        elif msg_type == 'switch_team':
            team = data.get('team')
            await self.switch_team(team)
        elif msg_type == 'start_game':
            await self.start_game()

    async def send_lobby_status(self):
        status = await self.get_lobby_status(self.game_id)

        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'lobby_update',
                'data': status
            }
        )

    async def lobby_update(self, event):
        await self.send(text_data=json.dumps(event['data']))

    def get_token_from_scope(self):
        from urllib.parse import parse_qs
        query_string = self.scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        token_list = params.get('token')
        if token_list:
            return token_list[0]
        return None

    @database_sync_to_async
    def get_user_by_token(self, token_key):
        """Получает пользователя по токену"""
        try:
            token = Token.objects.get(key=token_key)
            return token.user
        except Token.DoesNotExist:
            return None

    @database_sync_to_async
    def get_lobby_status(self, game_id):
        from .serializers import GameStatusSerializer

        game = Game.objects.get(game_id=game_id)

        return GameStatusSerializer(game).data

    @database_sync_to_async
    def _db_choose_role(self, role):
        from .models import PlayerGame, Game
        game = Game.objects.get(game_id=self.game_id)
        player = PlayerGame.objects.get(user=self.user, game=game)
        player.role = role
        player.save()

    async def choose_role(self, role):
        await self._db_choose_role(role)
        await self.send_lobby_status()

    @database_sync_to_async
    def _db_switch_team(self, team):
        from .models import PlayerGame, Game
        game = Game.objects.get(game_id=self.game_id)
        player = PlayerGame.objects.get(user=self.user, game=game)
        if player.team == team:
            return
        target_team_players = PlayerGame.objects.filter(game=game, team=team)
        if player.role == 'associator' and target_team_players.filter(role='associator').exists():
            return
        player.team = team
        player.save()

    async def switch_team(self, team):
        await self._db_switch_team(team)
        await self.send_lobby_status()

    @database_sync_to_async
    def _db_start_game(self):
        import random
        from .models import Game, Card
        from .utils import get_random_words, get_colors_distribution

        game = Game.objects.get(game_id=self.game_id)
        if game.status != 'waiting':
            return

        blue_has_assoc = PlayerGame.objects.filter(game=game, team='blue', role='associator').exists()
        blue_has_disas = PlayerGame.objects.filter(game=game, team='blue', role='disassociator').exists()
        red_has_assoc  = PlayerGame.objects.filter(game=game, team='red',  role='associator').exists()
        red_has_disas  = PlayerGame.objects.filter(game=game, team='red',  role='disassociator').exists()

        if not (blue_has_assoc and blue_has_disas and red_has_assoc and red_has_disas):
            return

        # Создаём карточки — точно так же, как в views.py::start_game
        words = get_random_words(25)
        colors = get_colors_distribution()
        cards_to_create = [
            Card(game=game, word=word, color=color, is_flipped=False, order_position=i)
            for i, (word, color) in enumerate(zip(words, colors))
        ]
        Card.objects.bulk_create(cards_to_create)

        first_team = random.choice(['blue', 'red'])
        game.status = 'active'
        game.current_turn_team = first_team
        game.turn_phase = 'hint'
        game.save()

    async def start_game(self):
        await self._db_start_game()
        await self.send_lobby_status()