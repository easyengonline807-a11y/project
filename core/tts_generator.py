#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генерация аудио через Gemini API
"""

import asyncio
import os
import time
import wave
from io import BytesIO
from typing import Optional, Tuple, List

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from config.constants import Config
from core.api_manager import AsyncAPIKeyManager
from utils.logger import ErrorLogger
from utils.ffmpeg_setup import AudioSegment, FFMPEG_AVAILABLE


class AsyncTTSGenerator:
    """Асинхронная генерация TTS с умной обработкой ошибок."""
    
    def __init__(self, key_manager: AsyncAPIKeyManager, 
                 error_logger: ErrorLogger):
        """Инициализация генератора."""
        self.key_manager = key_manager
        self.error_logger = error_logger
        self.use_mp3 = not FFMPEG_AVAILABLE
        
        if self.use_mp3:
            print("📁 Формат вывода: MP3 (ffmpeg недоступен)")
        else:
            print("📁 Формат вывода: WAV/MP3 (авто-определение)")
    
    async def generate_chunk(self, chunk_text: str, chunk_num: int,
                            keys_list: List[str], model: str, 
                            voice: str, style: str,
                            output_folder: str) -> Tuple[bool, Optional[str], str]:
        """Генерировать аудио для одного чанка."""
        start_time = time.time()
        final_text = f"{style} {chunk_text}" if style else chunk_text
        
        for attempt in range(Config.MAX_RETRIES + 1):
            key = await self.key_manager.get_best_key(keys_list, model)
            
            if not key:
                error_msg = "Все API ключи исчерпаны"
                self.error_logger.log_error(chunk_num, "N/A", "NO_KEYS", error_msg)
                return False, None, error_msg
            
            key_short = f"...{key[-8:]}"
            wait_time = await self.key_manager.get_wait_time(key, model)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            
            try:
                loop = asyncio.get_event_loop()
                audio_data = await loop.run_in_executor(
                    None, self._generate_sync, key, model, voice, final_text
                )
                
                output_file = await loop.run_in_executor(
                    None, self._save_audio_smart, audio_data, chunk_num, output_folder
                )
                
                duration = time.time() - start_time
                await self.key_manager.record_request(key)
                self.error_logger.log_success(chunk_num, key_short, duration)
                
                return True, output_file, ""
            
            except google_exceptions.ResourceExhausted as e:
                error_msg = "429: Лимит исчерпан"
                self.error_logger.log_error(chunk_num, key_short, "429", str(e))
                await self.key_manager.record_error(key, is_429=True)
                print(f"⚠️ Чанк #{chunk_num:02d}: 429, переключаюсь на другой ключ...")
                continue
            
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                self.error_logger.log_error(chunk_num, key_short, error_type, error_msg)
                
                if attempt < Config.MAX_RETRIES:
                    # ✅ ИСПРАВЛЕНИЕ: Защита от IndexError
                    if attempt < len(Config.RETRY_DELAYS):
                        delay = Config.RETRY_DELAYS[attempt]
                    else:
                        delay = Config.RETRY_DELAYS[-1]  # Используем последнее значение
                                                            
                    self.error_logger.log_retry(chunk_num, key_short, attempt + 1, error_type)
                    print(f"🔁 Чанк #{chunk_num:02d}: {error_type}, повтор через {delay} сек...")
                    await asyncio.sleep(delay)
                else:
                    await self.key_manager.record_error(key, is_429=False)
                    return False, None, f"{error_type}: {error_msg[:100]}"
        
        return False, None, "Превышено количество попыток"
    
    @staticmethod
    def _generate_sync(key: str, model: str, voice: str, text: str) -> bytes:
        """Синхронная генерация (для executor)."""
        genai.configure(api_key=key)
        model_obj = genai.GenerativeModel(model)
        
        response = model_obj.generate_content(
            text,
            generation_config={
                "response_modalities": ["AUDIO"],
                "speech_config": {
                    "voice_config": {
                        "prebuilt_voice_config": {
                            "voice_name": voice
                        }
                    }
                }
            }
        )
        
        return response.candidates[0].content.parts[0].inline_data.data
    
    def _save_audio_smart(self, audio_data: bytes, chunk_num: int, 
                         output_folder: str) -> str:
        """
        Умное сохранение аудио с корректной обработкой RAW PCM от Gemini API.
        
        Gemini API возвращает RAW PCM данные (16-bit, моно, 24 кГц) БЕЗ WAV заголовка.
        Необходимо добавить RIFF WAV заголовок для корректного воспроизведения.
        """
        from io import BytesIO
        
        os.makedirs(output_folder, exist_ok=True)
        
        # ✅ ИСПРАВЛЕНИЕ: audio_data уже bytes, НЕ нужно декодировать base64!
        audio_bytes = audio_data  # Используем напрямую
        
        # 📊 Логирование для отладки
        print(f"📦 Размер аудио данных: {len(audio_bytes)} байт")
        
        # Проверяем первые байты для определения формата
        magic_bytes = audio_bytes[:12] if len(audio_bytes) >= 12 else audio_bytes
        is_wav = magic_bytes.startswith(b'RIFF') and b'WAVE' in magic_bytes
        is_mp3 = magic_bytes.startswith(b'ID3') or (len(magic_bytes) >= 2 and magic_bytes[0:2] == b'\xff\xfb')
        
        if is_wav:
            # Уже готовый WAV с заголовком - сохраняем как есть
            output_file = os.path.join(output_folder, f"{chunk_num:02d}.wav")
            with open(output_file, 'wb') as f:
                f.write(audio_bytes)
            print(f"💾 Чанк #{chunk_num:02d} → WAV (готовый)")
            return output_file
        
        elif is_mp3:
            # MP3 формат - конвертируем в WAV или сохраняем как есть
            if FFMPEG_AVAILABLE:
                try:
                    audio_segment = AudioSegment.from_file(
                        BytesIO(audio_bytes), format="mp3"
                    )
                    output_file = os.path.join(output_folder, f"{chunk_num:02d}.wav")
                    audio_segment.export(output_file, format="wav")
                    print(f"💾 Чанк #{chunk_num:02d} → WAV (из MP3)")
                    return output_file
                except Exception as e:
                    print(f"⚠️ Ошибка конвертации MP3→WAV: {e}, сохраняю как MP3")
                    output_file = os.path.join(output_folder, f"{chunk_num:02d}.mp3")
                    with open(output_file, 'wb') as f:
                        f.write(audio_bytes)
                    return output_file
            else:
                # Нет FFmpeg - сохраняем MP3 как есть
                output_file = os.path.join(output_folder, f"{chunk_num:02d}.mp3")
                with open(output_file, 'wb') as f:
                    f.write(audio_bytes)
                print(f"💾 Чанк #{chunk_num:02d} → MP3")
                return output_file
        
        else:
            # ✅ RAW PCM от Gemini API - добавляем WAV заголовок
            print(f"🔧 Чанк #{chunk_num:02d} → RAW PCM, добавляю WAV заголовок...")
            
            try:
                # Создаём WAV файл с правильными параметрами
                output_file = os.path.join(output_folder, f"{chunk_num:02d}.wav")
                
                with wave.open(output_file, 'wb') as wf:
                    wf.setnchannels(1)       # Моно
                    wf.setsampwidth(2)        # 16-bit = 2 байта
                    wf.setframerate(24000)    # 24 кГц
                    wf.writeframes(audio_bytes)  # Записываем RAW PCM данные
                
                print(f"💾 Чанк #{chunk_num:02d} → WAV (добавлен заголовок)")
                
                # 🔍 Проверка корректности
                file_size = os.path.getsize(output_file)
                expected_size = len(audio_bytes) + 44  # 44 байта = размер WAV заголовка
                if abs(file_size - expected_size) > 10:
                    print(f"⚠️ Предупреждение: размер файла {file_size}, ожидалось ~{expected_size}")
                
                return output_file
            
            except Exception as e:
                # Если не удалось создать WAV - сохраняем как .bin для анализа
                print(f"❌ Ошибка создания WAV: {e}")
                output_file = os.path.join(output_folder, f"{chunk_num:02d}.bin")
                with open(output_file, 'wb') as f:
                    f.write(audio_bytes)
                print(f"⚠️ Чанк #{chunk_num:02d} → .bin (ошибка обработки)")
                return output_file
