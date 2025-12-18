#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Виджет отображения одного чанка
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox
import os
from typing import Optional

try:
    import pygame
    pygame.mixer.init()
except ImportError:
    pygame = None


class ChunkItemAsync(tk.Frame):
    """Виджет одного чанка с поддержкой фильтрации."""
    
    def __init__(self, parent, chunk_num: int, text: str,
                 on_generate, on_text_change):
        """Инициализация виджета чанка."""
        super().__init__(parent, relief='ridge', borderwidth=2)
        self.chunk_num = chunk_num
        self.on_generate = on_generate
        self.on_text_change = on_text_change
        self.audio_file: Optional[str] = None
        self.enabled_var = tk.BooleanVar(value=True)
        
        self._create_ui(text)
    
    def _create_ui(self, text: str) -> None:
        """Создать UI виджета."""
        # Заголовок
        header = tk.Frame(self)
        header.pack(fill='x', padx=5, pady=5)
        
        # Checkbutton для включения/выключения
        self.check_btn = tk.Checkbutton(
            header, variable=self.enabled_var,
            command=self._on_check_toggle
        )
        self.check_btn.pack(side='left', padx=(0, 5))
        
        tk.Label(header, text=f"Чанк {self.chunk_num:02d}",
                font=('Arial', 10, 'bold')).pack(side='left')
        
        self.char_count_label = tk.Label(
            header, text=f"({len(text)} символов)",
            font=('Arial', 8), fg='gray'
        )
        self.char_count_label.pack(side='left', padx=(5, 0))
        
        self.status_label = tk.Label(
            header, text="⏳ Ожидает",
            font=('Arial', 9), fg='orange'
        )
        self.status_label.pack(side='right')
        
        # Текстовое поле
        self.text_widget = scrolledtext.ScrolledText(
            self, wrap='word', font=('Arial', 9), height=4
        )
        self.text_widget.pack(fill='both', expand=True, padx=5, pady=5)
        self.text_widget.insert('1.0', text)
        
        def on_text_modified(event=None):
            current_text = self.text_widget.get('1.0', 'end-1c')
            self.char_count_label.config(text=f"({len(current_text)} символов)")
            self.on_text_change(self.chunk_num, current_text)
        
        self.text_widget.bind('<KeyRelease>', on_text_modified)
        
        # Кнопки
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill='x', padx=5, pady=(0, 5))
        
        self.gen_btn = tk.Button(
            btn_frame, text="🎙️ Генерировать",
            command=self._on_generate_click
        )
        self.gen_btn.pack(side='left', padx=(0, 5))
        
        self.play_btn = tk.Button(
            btn_frame, text="▶️ Воспроизвести",
            command=self._on_play_click, state='disabled'
        )
        self.play_btn.pack(side='left', padx=(0, 5))
        
        self.stop_btn = tk.Button(
            btn_frame, text="⏹️ Стоп",
            command=self._on_stop_click, state='disabled'
        )
        self.stop_btn.pack(side='left')
    
    def _on_check_toggle(self) -> None:
        """Обработка переключения чекбокса."""
        if self.enabled_var.get():
            self.text_widget.config(state='normal', bg='white')
            self.gen_btn.config(state='normal')
        else:
            self.text_widget.config(state='disabled', bg='#f0f0f0')
            self.gen_btn.config(state='disabled')
    
    def _on_generate_click(self) -> None:
        """Обработка клика на кнопку генерации."""
        self.on_generate(self.chunk_num)
    
    def _on_play_click(self) -> None:
        """Воспроизвести аудио."""
        if not self.audio_file or not os.path.exists(self.audio_file):
            messagebox.showerror("Ошибка", "Аудио файл не найден")
            return
        
        if pygame:
            try:
                pygame.mixer.music.load(self.audio_file)
                pygame.mixer.music.play()
                self.stop_btn.config(state='normal')
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка воспроизведения: {e}")
        else:
            messagebox.showinfo("Информация", 
                              f"Файл сохранён: {self.audio_file}\n\n"
                              "Для воспроизведения установите pygame:\n"
                              "pip install pygame")
    
    def _on_stop_click(self) -> None:
        """Остановить воспроизведение."""
        if pygame:
            pygame.mixer.music.stop()
            self.stop_btn.config(state='disabled')
    
    def is_enabled(self) -> bool:
        """Проверить, включен ли чанк."""
        return self.enabled_var.get()
    
    def get_text(self) -> str:
        """Получить текст чанка."""
        return self.text_widget.get('1.0', 'end-1c')
    
    def set_status(self, status: str, color: str = 'black') -> None:
        """Установить статус."""
        self.status_label.config(text=status, fg=color)
    
    def set_audio_file(self, filepath: str) -> None:
        """Установить путь к аудио файлу."""
        self.audio_file = filepath
        if filepath:
            self.play_btn.config(state='normal')
    
    def set_generating(self, is_generating: bool) -> None:
        """Установить состояние генерации."""
        if is_generating:
            self.gen_btn.config(state='disabled')
            self.text_widget.config(state='disabled')
        else:
            self.gen_btn.config(state='normal')
            if self.enabled_var.get():
                self.text_widget.config(state='normal')
