#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''Тест для определения кодов клавиш'''

import tkinter as tk

root = tk.Tk()
root.title('Тест горячих клавиш')
root.geometry('600x400')

info_label = tk.Label(root, text='Нажмите Ctrl + любую клавишу', 
                     font=('Arial', 14, 'bold'))
info_label.pack(pady=20)

results = tk.Text(root, font=('Courier', 10), height=15)
results.pack(fill='both', expand=True, padx=10, pady=10)

def show_key_info(event):
    '''Показать всю информацию о нажатой клавише.'''
    # Проверяем, нажат ли Ctrl
    ctrl_pressed = bool(event.state & 0x4)
    
    if ctrl_pressed:
        char_code = ord(event.char) if event.char else 'None'
        info = f'''
{'='*60}
Клавиша с Ctrl:
  char:        '{event.char}' (код: {char_code})
  keysym:      '{event.keysym}'
  keycode:     {event.keycode}
  state:       {event.state}
{'='*60}
'''
        results.insert('1.0', info)

root.bind('<KeyPress>', show_key_info)

instructions = '''
ИНСТРУКЦИЯ:
1. Переключитесь на РУССКУЮ раскладку
2. Нажмите Ctrl+П, Ctrl+Ы, Ctrl+К
3. Скопируйте результаты

4. Переключитесь на АНГЛИЙСКУЮ раскладку  
5. Нажмите Ctrl+G, Ctrl+S, Ctrl+R
6. Скопируйте результаты

7. Отправьте мне ВСЕ результаты!
'''

tk.Label(root, text=instructions, font=('Arial', 9), 
         justify='left', fg='blue').pack(pady=10)

root.mainloop()
