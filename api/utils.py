import random

WORDS_POOL = [
    "Море", "Солнце", "Лес", "Город", "Машина",
    "Книга", "Друг", "Время", "Дом", "Любовь",
    "Работа", "Счастье", "Путь", "Звезда", "Вода",
    "Огонь", "Земля", "Воздух", "Дерево", "Цветок",
    "Кошка", "Собака", "Птица", "Рыба", "Мысль",
]


def get_random_words(count=25):
    return random.sample(WORDS_POOL, count)


def get_colors_distribution():
    colors = ['blue'] * 9 + ['red'] * 9 + ['black'] * 7
    random.shuffle(colors)
    return colors
