#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Логирование ошибок в файл
"""

import logging
from config.constants import Config


class ErrorLogger:
    """Логирование ошибок в файл."""
    
    def __init__(self, log_file: str = Config.ERROR_LOG_FILE):
        """Инициализация логгера."""
        self.log_file = log_file
        
        # Настройка logging
        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format='%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger('GeminiTTS')
    
    def log_error(self, chunk_num: int, key_short: str, 
                  error_type: str, error_msg: str) -> None:
        """Залогировать ошибку."""
        self.logger.error(
            f"Чанк #{chunk_num:02d} | Ключ {key_short} | "
            f"{error_type}: {error_msg}"
        )
    
    def log_success(self, chunk_num: int, key_short: str, 
                   duration: float) -> None:
        """Залогировать успешную генерацию."""
        self.logger.info(
            f"✅ Чанк #{chunk_num:02d} | Ключ {key_short} | "
            f"Время: {duration:.1f} сек"
        )
    
    def log_retry(self, chunk_num: int, key_short: str, 
                 attempt: int, reason: str) -> None:
        """Залогировать повторную попытку."""
        self.logger.warning(
            f"🔁 Чанк #{chunk_num:02d} | Ключ {key_short} | "
            f"Попытка {attempt} | {reason}"
        )
