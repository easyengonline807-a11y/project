#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Главное окно приложения
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import asyncio
import os
import time
from datetime import datetime
from typing import Optional, List, Dict

try:
    import pygame
    pygame.mixer.init()
except ImportError:
    pygame = None

from config.constants import Config, MODELS, VOICES, STYLE_PRESETS
from config.settings import Settings
from core.api_manager import AsyncAPIKeyManager
from core.tts_generator import AsyncTTSGenerator
from core.text_processor import TextChunker
from core.audio_tools import AudioMerger
from core.progress_tracker import ProgressTracker
from gui.chunk_widget import ChunkItemAsync
from utils.logger import ErrorLogger
from utils.ffmpeg_setup import FFMPEG_AVAILABLE, FFmpegManager


class GeminiTTSAppAsync:
    """Главное окно приложения с асинхронной генерацией."""
    
    def __init__(self, root: tk.Tk):
        """Инициализация приложения."""
        self.root = root
        self.root.title("Gemini TTS v3.0 - Async Parallel Edition")
        self.root.geometry("1200x800")
        
        # Настройки и менеджеры
        self.settings = Settings()
        self.error_logger = ErrorLogger()
        self.key_manager = AsyncAPIKeyManager(self.error_logger)
        self.tts_generator = AsyncTTSGenerator(self.key_manager, self.error_logger)
        
        # Состояние
        self.api_keys: List[str] = []
        self.chunks_text: List[str] = []
        self.chunk_widgets: List[ChunkItemAsync] = []
        self.is_generating = False
        self.generation_task: Optional[asyncio.Task] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Создание UI
        self._create_ui()
        self._load_settings()
        self._setup_hotkeys()
        
        # Проверка ffmpeg
        FFmpegManager.show_warning_if_needed()
        
        print("=" * 70)
        print("🚀 Gemini TTS v3.0 - Async Parallel Edition")
        print("=" * 70)
    
    def _create_ui(self) -> None:
        """Создать пользовательский интерфейс."""
        # Главное меню
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Загрузить текст из файла", 
                            command=self._load_text_file)
        file_menu.add_command(label="Сохранить настройки", 
                            command=self._save_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Экспорт отчёта", 
                            command=self._export_report)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.quit)
        
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Инструменты", menu=tools_menu)
        tools_menu.add_command(label="Склеить все чанки", 
                             command=self._merge_all_chunks)
        tools_menu.add_command(label="Сбросить статистику ключей", 
                             command=self._reset_keys_stats)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Помощь", menu=help_menu)
        help_menu.add_command(label="Горячие клавиши", 
                            command=self._show_hotkeys)
        help_menu.add_command(label="О программе", 
                            command=self._show_about)
        
        # Панель настроек
        settings_frame = tk.LabelFrame(self.root, text="⚙️ Настройки", 
                                      font=('Arial', 10, 'bold'))
        settings_frame.pack(fill='x', padx=10, pady=5)
        
        # Первая строка настроек
        row1 = tk.Frame(settings_frame)
        row1.pack(fill='x', padx=5, pady=5)
        
        tk.Label(row1, text="Модель:").pack(side='left', padx=(0, 5))
        self.model_var = tk.StringVar(value=self.settings.data['model'])
        model_combo = ttk.Combobox(row1, textvariable=self.model_var, 
                                  values=MODELS, state='readonly', width=30)
        model_combo.pack(side='left', padx=(0, 20))
        model_combo.bind('<<ComboboxSelected>>', self._on_model_change)
        
        tk.Label(row1, text="Голос:").pack(side='left', padx=(0, 5))
        self.voice_var = tk.StringVar(value=self.settings.data['voice'])
        voice_combo = ttk.Combobox(row1, textvariable=self.voice_var, 
                                  values=VOICES, state='readonly', width=15)
        voice_combo.pack(side='left', padx=(0, 20))
        
        tk.Label(row1, text="Файл ключей:").pack(side='left', padx=(0, 5))
        self.keys_file_var = tk.StringVar(value=self.settings.data['keys_file'])
        keys_entry = tk.Entry(row1, textvariable=self.keys_file_var, width=20)
        keys_entry.pack(side='left', padx=(0, 5))
        
        tk.Button(row1, text="📂", command=self._browse_keys_file).pack(side='left', padx=(0, 5))
        tk.Button(row1, text="🔄 Загрузить", command=self._load_api_keys).pack(side='left')
        
        # Вторая строка настроек
        row2 = tk.Frame(settings_frame)
        row2.pack(fill='x', padx=5, pady=5)
        
        tk.Label(row2, text="Стиль:").pack(side='left', padx=(0, 5))
        self.style_var = tk.StringVar(value=self.settings.data.get('style', ''))
        style_combo = ttk.Combobox(row2, textvariable=self.style_var, 
                                  values=[""] + [s[1] for s in STYLE_PRESETS], 
                                  width=40)
        style_combo.pack(side='left', padx=(0, 20))
        
        tk.Label(row2, text="Размер чанка:").pack(side='left', padx=(0, 5))
        self.chunk_size_var = tk.IntVar(value=self.settings.data['chunk_size'])
        tk.Spinbox(row2, from_=500, to=5000, increment=100, 
                  textvariable=self.chunk_size_var, width=10).pack(side='left', padx=(0, 20))
        
        tk.Label(row2, text="Параллельность:").pack(side='left', padx=(0, 5))
        self.parallel_var = tk.IntVar(value=self.settings.data['max_parallel'])
        tk.Spinbox(row2, from_=1, to=20, 
                  textvariable=self.parallel_var, width=10).pack(side='left')
        
        # Статистика API ключей
        stats_frame = tk.LabelFrame(self.root, text="📊 Статистика API ключей", 
                                   font=('Arial', 10, 'bold'))
        stats_frame.pack(fill='x', padx=10, pady=5)
        
        self.stats_text = tk.Text(stats_frame, height=3, font=('Courier', 9))
        self.stats_text.pack(fill='x', padx=5, pady=5)
        self.stats_text.insert('1.0', "Загрузите API ключи для просмотра статистики")
        self.stats_text.config(state='disabled')
        
        # Ввод текста
        input_frame = tk.LabelFrame(self.root, text="📝 Исходный текст", 
                                   font=('Arial', 10, 'bold'))
        input_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.input_text = scrolledtext.ScrolledText(input_frame, wrap='word', 
                                                    font=('Arial', 10), height=8)
        self.input_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Кнопки управления
        control_frame = tk.Frame(self.root)
        control_frame.pack(fill='x', padx=10, pady=5)
        
        self.split_btn = tk.Button(control_frame, text="✂️ Разбить на чанки (Ctrl+S)", 
                                   command=self._split_text, font=('Arial', 10))
        self.split_btn.pack(side='left', padx=(0, 10))
        
        self.generate_btn = tk.Button(control_frame, text="🎙️ Генерировать всё (Ctrl+G)", 
                                     command=self._start_generation, 
                                     font=('Arial', 10, 'bold'), bg='#4CAF50', fg='white')
        self.generate_btn.pack(side='left', padx=(0, 10))
        
        self.stop_btn = tk.Button(control_frame, text="⏹️ Остановить", 
                                 command=self._stop_generation, 
                                 font=('Arial', 10), state='disabled', bg='#f44336', fg='white')
        self.stop_btn.pack(side='left', padx=(0, 10))
        
        self.merge_btn = tk.Button(control_frame, text="🔗 Склеить чанки", 
                                  command=self._merge_all_chunks, 
                                  font=('Arial', 10), state='disabled')
        self.merge_btn.pack(side='left')
        
        # Прогресс-бар
        progress_frame = tk.Frame(self.root)
        progress_frame.pack(fill='x', padx=10, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                           maximum=100)
        self.progress_bar.pack(fill='x', side='left', expand=True, padx=(0, 10))
        
        self.progress_label = tk.Label(progress_frame, text="Готов к работе", 
                                      font=('Arial', 9))
        self.progress_label.pack(side='left')
        
        # Список чанков
        chunks_frame = tk.LabelFrame(self.root, text="📦 Чанки", 
                                    font=('Arial', 10, 'bold'))
        chunks_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Canvas для прокрутки
        canvas = tk.Canvas(chunks_frame)
        scrollbar = tk.Scrollbar(chunks_frame, orient='vertical', command=canvas.yview)
        self.chunks_container = tk.Frame(canvas)
        
        self.chunks_container.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )
        
        canvas.create_window((0, 0), window=self.chunks_container, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Прокрутка колесом мыши
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
    def _setup_hotkeys(self) -> None:
        """Настроить горячие клавиши с поддержкой русской раскладки."""
        
        def handle_key(event):
            """Обработчик на основе keycode (физическая клавиша)."""
            # Проверяем Ctrl
            if not (event.state & 0x4):
                return
            
            keycode = event.keycode
            focused = self.root.focus_get()
            
            # ========== В ТЕКСТОВЫХ ПОЛЯХ ==========
            if isinstance(focused, (tk.Text, tk.Entry, scrolledtext.ScrolledText)):
                # Ctrl+C (keycode=67) - копировать
                if keycode == 67:
                    focused.event_generate("<<Copy>>")
                    return "break"
                
                # Ctrl+V (keycode=86) - вставить
                elif keycode == 86:
                    focused.event_generate("<<Paste>>")
                    return "break"
                
                # Ctrl+X (keycode=88) - вырезать
                elif keycode == 88:
                    focused.event_generate("<<Cut>>")
                    return "break"
                
                # Ctrl+A (keycode=65) - выделить всё
                elif keycode == 65:
                    if isinstance(focused, (tk.Text, scrolledtext.ScrolledText)):
                        focused.tag_add('sel', '1.0', 'end')
                    elif isinstance(focused, tk.Entry):
                        focused.select_range(0, 'end')
                    return "break"
                
                # Ctrl+Z (keycode=90) - отменить
                elif keycode == 90:
                    focused.event_generate("<<Undo>>")
                    return "break"
                
                # Остальное - пропускаем
                return
            
            # ========== ВНЕ ТЕКСТОВЫХ ПОЛЕЙ ==========
            # Ctrl+G (keycode=71) - генерация
            if keycode == 71:
                self._start_generation()
                return "break"
            
            # Ctrl+S (keycode=83) - разбить
            elif keycode == 83:
                self._split_text()
                return "break"
            
            # Ctrl+R (keycode=82) - сброс
            elif keycode == 82:
                self._reset_keys_stats()
                return "break"
        
        self.root.bind('<KeyPress>', handle_key)


    def _load_settings(self) -> None:
        """Загрузить сохранённые настройки."""
        self._load_api_keys()
    
    def _save_settings(self) -> None:
        """Сохранить текущие настройки."""
        self.settings.data.update({
            'model': self.model_var.get(),
            'voice': self.voice_var.get(),
            'style': self.style_var.get(),
            'keys_file': self.keys_file_var.get(),
            'chunk_size': self.chunk_size_var.get(),
            'max_parallel': self.parallel_var.get()
        })
        self.settings.save()
        messagebox.showinfo("Успех", "Настройки сохранены!")
    
    def _browse_keys_file(self) -> None:
        """Выбрать файл с API ключами."""
        filename = filedialog.askopenfilename(
            title="Выберите файл с API ключами",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            self.keys_file_var.set(filename)
            self._load_api_keys()
    
    def _load_api_keys(self) -> None:
        """Загрузить API ключи из файла."""
        keys_file = self.keys_file_var.get()
        self.api_keys = self.key_manager.load_keys_from_file(keys_file)
        self._update_stats_display()
    
    def _update_stats_display(self) -> None:
        """Обновить отображение статистики."""
        if not self.api_keys:
            self.stats_text.config(state='normal')
            self.stats_text.delete('1.0', 'end')
            self.stats_text.insert('1.0', "⚠️ API ключи не загружены")
            self.stats_text.config(state='disabled')
            return
        
        model = self.model_var.get()
        total_stats = self.key_manager.get_total_stats(self.api_keys, model)
        
        stats_str = (
            f"🔑 Всего ключей: {total_stats['total_keys']} | "
            f"✅ Активных: {total_stats['active_keys']} | "
            f"❌ Исчерпано: {total_stats['exhausted_keys']}\n"
            f"📊 Использовано: {total_stats['total_used']}/{total_stats['total_limit']} "
            f"({total_stats['percent']}%) | "
            f"💡 Доступно: {total_stats['total_remaining']} запросов"
        )
        
        self.stats_text.config(state='normal')
        self.stats_text.delete('1.0', 'end')
        self.stats_text.insert('1.0', stats_str)
        self.stats_text.config(state='disabled')
    
    def _on_model_change(self, event=None) -> None:
        """Обработчик изменения модели."""
        model = self.model_var.get()
        default_parallel = Config.DEFAULT_PARALLEL.get(model, 15)
        self.parallel_var.set(default_parallel)
        self._update_stats_display()
    
    def _load_text_file(self) -> None:
        """Загрузить текст из файла."""
        filename = filedialog.askopenfilename(
            title="Выберите текстовый файл",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    text = f.read()
                self.input_text.delete('1.0', 'end')
                self.input_text.insert('1.0', text)
                messagebox.showinfo("Успех", f"Загружено {len(text)} символов")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить файл:\n{e}")
    
    def _split_text(self) -> None:
        """Разбить текст на чанки."""
        text = self.input_text.get('1.0', 'end-1c').strip()
        
        if not text:
            messagebox.showwarning("Предупреждение", "Введите текст для разбивки")
            return
        
        chunk_size = self.chunk_size_var.get()
        self.chunks_text = TextChunker.split_by_paragraphs(text, max_chars=chunk_size)
        
        # Очистить предыдущие виджеты
        for widget in self.chunk_widgets:
            widget.destroy()
        self.chunk_widgets.clear()
        
        # Создать новые виджеты чанков
        for i, chunk_text in enumerate(self.chunks_text, 1):
            widget = ChunkItemAsync(
                self.chunks_container, i, chunk_text,
                on_generate=self._generate_single_chunk,
                on_text_change=self._on_chunk_text_change
            )
            widget.pack(fill='x', padx=5, pady=5)
            self.chunk_widgets.append(widget)
        
        messagebox.showinfo("Успех", f"Текст разбит на {len(self.chunks_text)} чанков")
    
    def _on_chunk_text_change(self, chunk_num: int, new_text: str) -> None:
        """Обработчик изменения текста чанка."""
        if 0 < chunk_num <= len(self.chunks_text):
            self.chunks_text[chunk_num - 1] = new_text
    
    def _generate_single_chunk(self, chunk_num: int) -> None:
        """Генерировать один чанк."""
        if not self.api_keys:
            messagebox.showwarning("Предупреждение", "Сначала загрузите API ключи")
            return
        
        if self.is_generating:
            messagebox.showwarning("Предупреждение", "Генерация уже выполняется")
            return
        
        # Запуск генерации одного чанка
        threading.Thread(target=self._run_single_chunk_generation, 
                        args=(chunk_num,), daemon=True).start()
    
    def _run_single_chunk_generation(self, chunk_num: int) -> None:
        """Запустить генерацию одного чанка в отдельном потоке."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_until_complete(self._generate_chunk_async(chunk_num))
        finally:
            self.loop.close()
    
    async def _generate_chunk_async(self, chunk_num: int) -> None:
        """Асинхронная генерация одного чанка."""
        widget = self.chunk_widgets[chunk_num - 1]
        chunk_text = widget.get_text()
        
        widget.set_status("🔄 Генерация...", "blue")
        widget.set_generating(True)
        
        model = self.model_var.get()
        voice = self.voice_var.get()
        style = self.style_var.get()
        output_folder = self.settings.data['output_folder']
        
        success, audio_file, error_msg = await self.tts_generator.generate_chunk(
            chunk_text, chunk_num, self.api_keys, model, voice, style, output_folder
        )
        
        if success:
            widget.set_status("✅ Готово", "green")
            widget.set_audio_file(audio_file)
            self._play_sound()
        else:
            widget.set_status(f"❌ Ошибка: {error_msg[:50]}", "red")
        
        widget.set_generating(False)
        self._update_stats_display()
    
    def _start_generation(self) -> None:
        """Начать генерацию всех чанков."""
        if not self.api_keys:
            messagebox.showwarning("Предупреждение", "Сначала загрузите API ключи")
            return
        
        if not self.chunk_widgets:
            messagebox.showwarning("Предупреждение", "Сначала разбейте текст на чанки")
            return
        
        if self.is_generating:
            messagebox.showwarning("Предупреждение", "Генерация уже выполняется")
            return
        
        self.is_generating = True
        self.generate_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.split_btn.config(state='disabled')
        
        # Запуск генерации в отдельном потоке
        threading.Thread(target=self._run_generation, daemon=True).start()
    
    def _run_generation(self) -> None:
        """Запустить генерацию в отдельном потоке."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_until_complete(self._generate_all_chunks())
        finally:
            self.loop.close()
            self.is_generating = False
            self.root.after(0, self._on_generation_complete)
    
    async def _generate_all_chunks(self) -> None:
        """Асинхронная генерация всех чанков."""
        # Подготовка
        enabled_chunks = [(i, w) for i, w in enumerate(self.chunk_widgets, 1) if w.is_enabled()]
        
        if not enabled_chunks:
            self.root.after(0, lambda: messagebox.showinfo("Информация", 
                                                          "Нет включенных чанков для генерации"))
            return
        
        total_enabled = len(enabled_chunks)
        tracker = ProgressTracker(total_enabled)
        
        model = self.model_var.get()
        voice = self.voice_var.get()
        style = self.style_var.get()
        output_folder = self.settings.data['output_folder']
        max_parallel = self.parallel_var.get()
        
        # Семафор для ограничения параллельности
        semaphore = asyncio.Semaphore(max_parallel)
        
        async def generate_with_semaphore(chunk_num: int, widget: ChunkItemAsync):
            async with semaphore:
                await tracker.start_chunk()
                self.root.after(0, lambda: widget.set_status("🔄 Генерация...", "blue"))
                self.root.after(0, lambda: widget.set_generating(True))
                
                chunk_text = widget.get_text()
                success, audio_file, error_msg = await self.tts_generator.generate_chunk(
                    chunk_text, chunk_num, self.api_keys, model, voice, style, output_folder
                )
                
                if success:
                    duration = time.time() - tracker.start_time
                    await tracker.complete_chunk(duration)
                    self.root.after(0, lambda w=widget, f=audio_file: (
                        w.set_status("✅ Готово", "green"),
                        w.set_audio_file(f)
                    ))
                else:
                    await tracker.fail_chunk()
                    self.root.after(0, lambda w=widget, e=error_msg: 
                                  w.set_status(f"❌ {e[:50]}", "red"))
                
                self.root.after(0, lambda w=widget: w.set_generating(False))
                self.root.after(0, self._update_stats_display)
                self.root.after(0, lambda: self._update_progress(tracker))
        
        # Запуск всех задач
        tasks = [generate_with_semaphore(num, widget) for num, widget in enabled_chunks]
        await asyncio.gather(*tasks)
        
        # Финальное обновление
        self.root.after(0, lambda: self._update_progress(tracker))
        self.root.after(0, self._play_sound)
    
    def _update_progress(self, tracker: ProgressTracker) -> None:
        """Обновить прогресс-бар."""
        stats = tracker.get_stats()
        self.progress_var.set(stats['percent'])
        self.progress_label.config(
            text=f"✅ {stats['completed']}/{stats['total']} | "
                 f"⏳ {stats['in_progress']} | "
                 f"❌ {stats['failed']} | "
                 f"ETA: {stats['eta']}"
        )
    
    def _on_generation_complete(self) -> None:
        """Обработчик завершения генерации."""
        self.generate_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.split_btn.config(state='normal')
        self.merge_btn.config(state='normal')
        
        messagebox.showinfo("Готово", "Генерация завершена!")
    
    def _stop_generation(self) -> None:
        """Остановить генерацию."""
        if self.loop and self.loop.is_running():
            self.loop.stop()
        self.is_generating = False
        self.generate_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.split_btn.config(state='normal')
    
    def _merge_all_chunks(self) -> None:
        """Склеить все чанки в один файл."""
        output_folder = self.settings.data['output_folder']
        
        if not os.path.exists(output_folder):
            messagebox.showwarning("Предупреждение", "Папка с чанками не найдена")
            return
        
        # Собрать все файлы чанков
        chunk_files = []
        for i in range(1, len(self.chunk_widgets) + 1):
            chunk_file = os.path.join(output_folder, f"{i:02d}.wav")
            if os.path.exists(chunk_file):
                chunk_files.append(chunk_file)
        
        if not chunk_files:
            messagebox.showwarning("Предупреждение", "Нет сгенерированных чанков для склейки")
            return
        
        # Выбрать имя выходного файла
        output_file = filedialog.asksaveasfilename(
            title="Сохранить объединённый файл",
            defaultextension=".wav",
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")]
        )
        
        if not output_file:
            return
        
        # Склейка
        success = AudioMerger.merge_chunks(chunk_files, output_file)
        
        if success:
            messagebox.showinfo("Успех", f"Файл сохранён:\n{output_file}")
        else:
            messagebox.showerror("Ошибка", "Не удалось склеить файлы")
    
    def _reset_keys_stats(self) -> None:
        """Сбросить статистику ключей."""
        result = messagebox.askyesno("Подтверждение", 
                                    "Сбросить статистику всех API ключей?")
        if result:
            self.key_manager.reset_all_stats()
            self._update_stats_display()
            messagebox.showinfo("Успех", "Статистика сброшена")
    
    def _export_report(self) -> None:
        """Экспортировать отчёт о генерации."""
        filename = filedialog.asksaveasfilename(
            title="Сохранить отчёт",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=" * 70 + "\n")
                f.write("ОТЧЁТ О ГЕНЕРАЦИИ - Gemini TTS v3.0\n")
                f.write("=" * 70 + "\n\n")
                f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Модель: {self.model_var.get()}\n")
                f.write(f"Голос: {self.voice_var.get()}\n")
                f.write(f"Всего чанков: {len(self.chunk_widgets)}\n\n")
                
                model = self.model_var.get()
                total_stats = self.key_manager.get_total_stats(self.api_keys, model)
                
                f.write("СТАТИСТИКА API КЛЮЧЕЙ:\n")
                f.write(f"Всего ключей: {total_stats['total_keys']}\n")
                f.write(f"Активных: {total_stats['active_keys']}\n")
                f.write(f"Исчерпано: {total_stats['exhausted_keys']}\n")
                f.write(f"Использовано запросов: {total_stats['total_used']}/{total_stats['total_limit']}\n\n")
            
            messagebox.showinfo("Успех", f"Отчёт сохранён:\n{filename}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить отчёт:\n{e}")
    
    def _show_hotkeys(self) -> None:
        """Показать справку по горячим клавишам."""
        help_text = """
╔════════════════════════════════════════════════════════════════╗
║                    ГОРЯЧИЕ КЛАВИШИ                             ║
╚════════════════════════════════════════════════════════════════╝

Ctrl+G  - Генерировать все чанки
Ctrl+S  - Разбить текст на чанки
Ctrl+R  - Сбросить статистику API ключей

Примечание: Работают на русской и английской раскладке
════════════════════════════════════════════════════════════════
        """
        messagebox.showinfo("Горячие клавиши", help_text)
    
    def _show_about(self) -> None:
        """Показать информацию о программе."""
        about_text = """
╔════════════════════════════════════════════════════════════════╗
║              Gemini TTS v3.0                                   ║
║         Async Parallel Edition                                 ║
╚════════════════════════════════════════════════════════════════╝

Асинхронная параллельная генерация речи через Gemini API

Особенности:
✅ Параллельная обработка до 15 чанков
✅ Умная ротация API ключей
✅ Автоматическое восстановление при ошибках
✅ Детальная статистика использования

FFmpeg: """ + ("✅ Установлен" if FFMPEG_AVAILABLE else "❌ Не найден") + """

© 2024 Gemini TTS Project
════════════════════════════════════════════════════════════════
        """
        messagebox.showinfo("О программе", about_text)
    
    def _play_sound(self) -> None:
        """Воспроизвести звук уведомления."""
        if Config.ENABLE_SOUND and pygame:
            try:
                # Системный beep через pygame
                pygame.mixer.Sound.play(pygame.mixer.Sound(buffer=b'\x00\xff' * 1000))
            except:
                pass
