#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Конфигурация и константы приложения
"""

class Config:
    """Глобальная конфигурация."""
    
    # Лимиты моделей (Free tier)
    LIMITS = {
        'gemini-2.5-flash-preview-tts': {
            'rpd': 250,  # Requests per day
            'rpm': 15,   # Requests per minute
            'delay': 4.0  # Секунд между запросами
        },
        'gemini-2.5-pro-preview-tts': {
            'rpd': 100,
            'rpm': 5,
            'delay': 12.0
        }
    }
    
    # Параллельность (по умолчанию)
    DEFAULT_PARALLEL = {
        'gemini-2.5-flash-preview-tts': 15,
        'gemini-2.5-pro-preview-tts': 8
    }
    
    # Retry настройки
    MAX_RETRIES = 2  # Максимум попыток для сетевых ошибок
    RETRY_DELAYS = [2, 5]  # Секунды задержки между попытками
    
    # Файлы
    STATS_FILE = "api_keys_stats.json"
    SETTINGS_FILE = "settings.json"
    ERROR_LOG_FILE = "generation_errors.log"
    PROGRESS_FILE = "generation_progress.json"
    
    # Звук уведомления (системный beep)
    ENABLE_SOUND = True


# Доступные модели
MODELS = [
    'gemini-2.5-flash-preview-tts',
    'gemini-2.5-pro-preview-tts'
]

# Доступные голоса
VOICES = [
    'Achernar', 'Achird', 'Algenib', 'Algieba', 'Alnilam',
    'Aoede', 'Autonoe', 'Callirrhoe', 'Charon', 'Despina',
    'Enceladus', 'Erinome', 'Fenrir', 'Gacrux', 'Iapetus',
    'Kore', 'Laomedeia', 'Leda', 'Orus', 'Puck',
    'Pulcherrima', 'Rasalgethi', 'Sadachbia', 'Sadaltager', 'Schedar',
    'Sulafat', 'Umbriel', 'Vindemiatrix', 'Zephyr', 'Zubenelgenubi'
]

# Пресеты стилей
STYLE_PRESETS = [
    ("🎉 Весело", "Say excitedly:"),
    ("😊 Дружелюбно", "Read aloud in a warm and friendly tone:"),
    ("🤫 Шепотом", "Whisper mysteriously:"),
    ("📢 Драматично", "Say dramatically:")
]
