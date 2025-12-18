import tkinter as tk
from gui.chunk_widget import ChunkItemAsync

print('✅ ChunkItemAsync импортирован!')

# Создаём тестовое окно
root = tk.Tk()
root.withdraw()  # Скрываем окно

def dummy_gen(num):
    print(f'Генерация чанка {num}')

def dummy_change(num, text):
    pass

# Создаём виджет чанка
chunk = ChunkItemAsync(root, 1, 'Тестовый текст', dummy_gen, dummy_change)

print('✅ Виджет ChunkItemAsync создан!')
print('Всё работает!')

root.destroy()
