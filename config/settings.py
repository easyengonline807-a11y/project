#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Управление пользовательскими настройками
"""

import json
import os
from config.constants import Config


class Settings:
    """Управление настройками приложения."""
    
    def __init__(self):
        """Инициализация настроек."""
        self.file = Config.SETTINGS_FILE
        self.defaults = {
            'model': 'gemini-2.5-flash-preview-tts',
            'voice': 'Puck',
            'style': '',
            'keys_file': 'api_keys.txt',
            'output_folder': 'output',
            'chunk_size': 3000,
            'max_parallel': 15,  # Автоматически для flash
            'enable_sound': True
        }
        self.data = self.defaults.copy()
        self.load()
    
    def load(self) -> None:
        """Загрузить настройки из файла."""
        if os.path.exists(self.file):
            try:
                with open(self.file, 'r', encoding='utf-8') as f:
                    self.data.update(json.load(f))
                print("✅ Настройки загружены")
            except Exception as e:
                print(f"⚠️ Ошибка загрузки настроек: {e}")
    
    def save(self) -> None:
        """Сохранить настройки в файл."""
        try:
            with open(self.file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
