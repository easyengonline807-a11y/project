#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gemini TTS v3.0 - Async Parallel Edition
Точка входа приложения
"""

import tkinter as tk
from gui.main_window import GeminiTTSAppAsync


def main():
    """Запуск приложения."""
    root = tk.Tk()
    app = GeminiTTSAppAsync(root)
    root.mainloop()


if __name__ == "__main__":
    main()
