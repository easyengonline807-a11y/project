#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Инструменты для работы с аудио файлами
"""

import os
from typing import List
from utils.ffmpeg_setup import AudioSegment


class AudioMerger:
    """Склейка аудио файлов."""
    
    @staticmethod
    def merge_chunks(chunk_files: List[str], output_file: str) -> bool:
        """
        Склеить чанки в один файл.
        
        Args:
            chunk_files: Список путей к аудио файлам (в правильном порядке)
            output_file: Путь к выходному файлу
        
        Returns:
            True если успешно, False иначе
        """
        try:
            combined = AudioSegment.empty()
            
            for i, chunk_file in enumerate(chunk_files, 1):
                if not os.path.exists(chunk_file):
                    print(f"⚠️ Файл {chunk_file} не найден, пропускаю")
                    continue
                
                audio = AudioSegment.from_file(chunk_file, format="wav")
                combined += audio
                print(f"🔗 Склеен чанк {i}/{len(chunk_files)}")
            
            combined.export(output_file, format="wav")
            print(f"✅ Файл сохранён: {output_file}")
            return True
        
        except Exception as e:
            print(f"❌ Ошибка склейки: {e}")
            return False
