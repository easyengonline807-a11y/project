#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Управление API ключами с умной ротацией
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from config.constants import Config
from utils.logger import ErrorLogger


class AsyncAPIKeyManager:
    """Асинхронное управление API ключами с умной ротацией."""
    
    def __init__(self, error_logger: ErrorLogger):
        """Инициализация менеджера ключей."""
        self.stats_file = Config.STATS_FILE
        self.keys_data: Dict = {}
        self.error_logger = error_logger
        self.lock = asyncio.Lock()
        self.load_stats()
    
    def load_keys_from_file(self, filepath: str) -> List[str]:
        """Загрузить API ключи из файла."""
        if not os.path.exists(filepath):
            return []
        
        keys = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    key = line.strip()
                    if key and not key.startswith('#'):
                        keys.append(key)
                        if key not in self.keys_data:
                            self.keys_data[key] = {
                                'requests_today': 0,
                                'reset_time': None,
                                'last_request': 0,
                                'exhausted': False,
                                'error_count': 0
                            }
            print(f"✅ Загружено {len(keys)} API ключей")
        except Exception as e:
            print(f"❌ Ошибка чтения ключей: {e}")
        
        return keys
    
    def load_stats(self) -> None:
        """Загрузить статистику из файла."""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    self.keys_data = json.load(f)
                    self._check_all_resets()
            except Exception as e:
                print(f"⚠️ Ошибка загрузки статистики: {e}")
    
    def save_stats(self) -> None:
        """Сохранить статистику в файл."""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.keys_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ Ошибка сохранения статистики: {e}")
    
    def _check_all_resets(self) -> None:
        """Проверить и сбросить счётчики для всех ключей."""
        now = datetime.now()
        
        for key in self.keys_data:
            reset_str = self.keys_data[key].get('reset_time')
            
            if reset_str:
                try:
                    reset_time = datetime.fromisoformat(reset_str)
                    if now >= reset_time:
                        print(f"🔄 Сброс ключа ...{key[-8:]}")
                        self.keys_data[key]['requests_today'] = 0
                        self.keys_data[key]['exhausted'] = False
                        self.keys_data[key]['error_count'] = 0
                        tomorrow = now.date() + timedelta(days=1)
                        self.keys_data[key]['reset_time'] = datetime.combine(
                            tomorrow, datetime.min.time()
                        ).isoformat()
                except Exception:
                    pass
            else:
                tomorrow = now.date() + timedelta(days=1)
                self.keys_data[key]['reset_time'] = datetime.combine(
                    tomorrow, datetime.min.time()
                ).isoformat()
    
    async def get_best_key(self, keys_list: List[str], model: str) -> Optional[str]:
        """
        Получить лучший доступный ключ (с максимальным остатком лимита).
        
        Приоритет:
        1. Ключи без ошибок
        2. Максимальный остаток лимита
        3. Наименьшее количество запросов сегодня
        """
        async with self.lock:
            self._check_all_resets()
            
            limit = Config.LIMITS[model]['rpd']
            available_keys = []
            
            for key in keys_list:
                if key not in self.keys_data:
                    self.keys_data[key] = {
                        'requests_today': 0,
                        'reset_time': None,
                        'last_request': 0,
                        'exhausted': False,
                        'error_count': 0
                    }
                    self._check_all_resets()
                
                stats = self.keys_data[key]
                
                if not stats['exhausted'] and stats['requests_today'] < limit:
                    remaining = limit - stats['requests_today']
                    priority = (
                        -stats['error_count'],  # Меньше ошибок = выше приоритет
                        remaining,               # Больше остаток = выше приоритет
                        -stats['requests_today'] # Меньше использован = выше приоритет
                    )
                    available_keys.append((key, priority))
            
            if not available_keys:
                print("❌ Все ключи исчерпаны!")
                return None
            
            # Сортируем по приоритету и берём лучший
            available_keys.sort(key=lambda x: x[1], reverse=True)
            best_key = available_keys[0][0]
            
            remaining = limit - self.keys_data[best_key]['requests_today']
            print(f"🔑 Выбран ключ ...{best_key[-8:]} (остаток: {remaining}/{limit})")
            
            return best_key
    
    async def record_request(self, key: str) -> None:
        """Записать выполненный запрос."""
        async with self.lock:
            if key in self.keys_data:
                self.keys_data[key]['requests_today'] += 1
                self.keys_data[key]['last_request'] = time.time()
                self.save_stats()
    
    async def record_error(self, key: str, is_429: bool = False) -> None:
        """Записать ошибку для ключа."""
        async with self.lock:
            if key in self.keys_data:
                self.keys_data[key]['error_count'] += 1
                
                if is_429:
                    # Для 429 помечаем ключ как исчерпанный
                    self.keys_data[key]['exhausted'] = True
                    print(f"⚠️ Ключ ...{key[-8:]} исчерпан (429)")
                
                self.save_stats()
    
    async def get_wait_time(self, key: str, model: str) -> float:
        """Получить время ожидания для соблюдения RPM."""
        if key not in self.keys_data:
            return 0
        
        rpm_delay = Config.LIMITS[model]['delay']
        elapsed = time.time() - self.keys_data[key]['last_request']
        wait = max(0, rpm_delay - elapsed)
        
        return wait
    
    def get_key_stats(self, key: str, model: str) -> Tuple[int, int, int, int, bool]:
        """Получить статистику по ключу."""
        if key not in self.keys_data:
            return 0, 0, 0, 0, False
        
        limit = Config.LIMITS[model]['rpd']
        stats = self.keys_data[key]
        
        if stats['exhausted']:
            return limit, 0, limit, 100, True
        
        used = stats['requests_today']
        remaining = limit - used
        percent = int((used / limit) * 100) if limit > 0 else 0
        
        return used, remaining, limit, percent, False
    
    def get_total_stats(self, keys_list: List[str], model: str) -> Dict:
        """Получить общую статистику по всем ключам."""
        limit = Config.LIMITS[model]['rpd']
        total_limit = limit * len(keys_list)
        total_used = 0
        active_keys = 0
        exhausted_keys = 0
        
        for key in keys_list:
            if key in self.keys_data:
                stats = self.keys_data[key]
                
                if stats['exhausted']:
                    total_used += limit
                    exhausted_keys += 1
                else:
                    total_used += stats['requests_today']
                    active_keys += 1
            else:
                active_keys += 1
        
        total_remaining = total_limit - total_used
        percent = int((total_used / total_limit) * 100) if total_limit > 0 else 0
        
        return {
            'total_keys': len(keys_list),
            'active_keys': active_keys,
            'exhausted_keys': exhausted_keys,
            'total_used': total_used,
            'total_remaining': total_remaining,
            'total_limit': total_limit,
            'percent': percent
        }
    
    def reset_all_stats(self) -> None:
        """Сбросить статистику всех ключей."""
        for key in self.keys_data:
            self.keys_data[key]['requests_today'] = 0
            self.keys_data[key]['exhausted'] = False
            self.keys_data[key]['error_count'] = 0
        self.save_stats()
        print("✅ Статистика всех ключей сброшена")
