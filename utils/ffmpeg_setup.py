#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Настройка FFmpeg для работы с аудио
"""

import os


def setup_ffmpeg():
    """Настроить ffmpeg перед импортом pydub."""
    try:
        import imageio_ffmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        
        # Настройка переменных окружения ДО импорта pydub
        os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_path
        
        # Добавляем директорию ffmpeg в PATH
        ffmpeg_dir = os.path.dirname(ffmpeg_path)
        if ffmpeg_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
        
        # Подавляем warning от pydub
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=RuntimeWarning, 
                                  message=".*ffmpeg.*")
            from pydub import AudioSegment
        
        # Настройка pydub
        AudioSegment.converter = ffmpeg_path
        AudioSegment.ffmpeg = ffmpeg_path
        AudioSegment.ffprobe = ffmpeg_path.replace("ffmpeg", "ffprobe")
        
        print(f"✅ ffmpeg настроен: {ffmpeg_path}")
        return AudioSegment, True
    except ImportError:
        print("⚠️ imageio-ffmpeg не установлен")
        print("Попытка импорта pydub без ffmpeg...")
        try:
            from pydub import AudioSegment
            return AudioSegment, False
        except ImportError as e:
            print(f"❌ Критическая ошибка: {e}")
            return None, False


class FFmpegManager:
    """Проверка ffmpeg."""
    
    @staticmethod
    def is_available() -> bool:
        """Проверить доступность ffmpeg."""
        return FFMPEG_AVAILABLE
    
    @staticmethod
    def get_format() -> str:
        """Получить рекомендуемый формат."""
        return "wav" if FFMPEG_AVAILABLE else "mp3"
    
    @staticmethod
    def show_warning_if_needed():
        """Показать предупреждение если ffmpeg недоступен."""
        if not FFMPEG_AVAILABLE:
            msg = """
╔════════════════════════════════════════════════════════════════╗
║               FFMPEG НЕ НАЙДЕН                                 ║
╚════════════════════════════════════════════════════════════════╝

Файлы будут сохраняться в формате MP3 вместо WAV.

Для работы с WAV установите:
  pip install imageio-ffmpeg

Затем перезапустите программу.
════════════════════════════════════════════════════════════════
"""
            print(msg)
            return msg
        return None


# Вызываем настройку ffmpeg при импорте модуля
AudioSegment, FFMPEG_AVAILABLE = setup_ffmpeg()

if AudioSegment is None:
    print("❌ Не удалось импортировать pydub!")
    print("Установите: pip install pydub imageio-ffmpeg")
    exit(1)
