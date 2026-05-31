from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    games_played = models.IntegerField(default=0)
    games_won = models.IntegerField(default=0)

    @property
    def winrate(self):
        if self.games_played == 0:
            return 0
        return round((self.games_won / self.games_played) * 100, 1)

    def __str__(self):
        return f"Profile of {self.user.username}"


class Game(models.Model):
    STATUS_CHOICES = [
        ('waiting', 'Ожидание'),
        ('active', 'В процессе'),
        ('finished', 'Завершена'),
    ]

    PHASE_CHOICES = [
        ('hint', 'Ассоциатор дает подсказку'),
        ('guess', 'Десоциаторы угадывают'),
    ]

    game_id = models.CharField(max_length=10, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='waiting')
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    winner_team = models.CharField(max_length=5, null=True, blank=True)
    current_turn_team = models.CharField(max_length=5, null=True, blank=True)
    turn_phase = models.CharField(max_length=10, choices=PHASE_CHOICES, default='hint')
    current_turn_word = models.CharField(max_length=50, null=True, blank=True)
    red_score = models.IntegerField(default=0)
    blue_score = models.IntegerField(default=0)

    def __str__(self):
        return f"Game {self.game_id}"


class PlayerGame(models.Model):
    TEAM_CHOICES = [
        ('blue', 'Синяя'),
        ('red', 'Красная'),
    ]
    ROLE_CHOICES = [
        ('associator', 'Ассоциатор'),
        ('disassociator', 'Десоциатор'),
        ('none', 'Нет роли')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    team = models.CharField(max_length=5, choices=TEAM_CHOICES)
    role = models.CharField(max_length=15, choices=ROLE_CHOICES)
    score = models.IntegerField(default=0)

    class Meta:
        unique_together = ['user', 'game']

    def __str__(self):
        return f"{self.user.username} in {self.game.game_id}"


class Card(models.Model):
    COLOR_CHOICES = [
        ('blue', 'Blue'),
        ('red', 'Red'),
        ('black', 'Black'),
        ('unknown', 'Unknown')
    ]

    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    word = models.CharField(max_length=50)
    color = models.CharField(max_length=10, choices=COLOR_CHOICES)
    is_flipped = models.BooleanField(default=False)
    order_position = models.IntegerField()
    flipped_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.word} ({self.color})"


class ChatMessage(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    team = models.CharField(max_length=5, null=True, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
