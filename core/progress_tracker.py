#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Отслеживание прогресса генерации
"""

import asyncio
import time
from typing import List, Dict


class ProgressTracker:
    """Отслеживание прогресса генерации с оценкой времени."""
    
    def __init__(self, total_chunks: int):
        """Инициализация трекера."""
        self.total = total_chunks
        self.completed = 0
        self.in_progress = 0
        self.failed = 0
        self.skipped = 0
        self.start_time = time.time()
        self.chunk_times: List[float] = []
        self.lock = asyncio.Lock()
    
    async def start_chunk(self) -> None:
        """Отметить начало обработки чанка."""
        async with self.lock:
            self.in_progress += 1
    
    async def complete_chunk(self, duration: float) -> None:
        """Отметить завершение чанка."""
        async with self.lock:
            self.completed += 1
            self.in_progress = max(0, self.in_progress - 1)
            self.chunk_times.append(duration)
    
    async def fail_chunk(self) -> None:
        """Отметить неудачу чанка."""
        async with self.lock:
            self.failed += 1
            self.in_progress = max(0, self.in_progress - 1)
    
    async def skip_chunk(self) -> None:
        """Отметить пропуск чанка."""
        async with self.lock:
            self.skipped += 1
    
    def get_stats(self) -> Dict:
        """Получить статистику."""
        pending = self.total - self.completed - self.failed - self.skipped
        percent = int((self.completed / self.total) * 100) if self.total > 0 else 0
        
        # Оценка оставшегося времени
        eta_seconds = 0
        if self.chunk_times and pending > 0:
            avg_time = sum(self.chunk_times) / len(self.chunk_times)
            eta_seconds = avg_time * pending
        
        eta_str = self._format_time(eta_seconds)
        elapsed_str = self._format_time(time.time() - self.start_time)
        
        return {
            'total': self.total,
            'completed': self.completed,
            'in_progress': self.in_progress,
            'pending': pending,
            'failed': self.failed,
            'skipped': self.skipped,
            'percent': percent,
            'eta': eta_str,
            'elapsed': elapsed_str
        }
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """Форматировать время."""
        if seconds < 60:
            return f"{int(seconds)} сек"
        elif seconds < 3600:
            return f"{int(seconds / 60)} мин {int(seconds % 60)} сек"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours} ч {minutes} мин"
