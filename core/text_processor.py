#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработка текста: разбивка на чанки
"""

import re
from typing import List


class TextChunker:
    """Разбивка текста на чанки по абзацам."""
    
    @staticmethod
    def split_by_paragraphs(text: str, max_chars: int = 3000,
                           tolerance: float = 0.10) -> List[str]:
        """Разбить текст на чанки с учётом абзацев и допуска."""
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_length = len(para)
            
            if not current_chunk:
                current_chunk.append(para)
                current_length = para_length
                continue
            
            new_length = current_length + para_length + 2
            
            if current_length < max_chars:
                if new_length <= max_chars:
                    current_chunk.append(para)
                    current_length = new_length
                else:
                    max_allowed = max_chars * (1 + tolerance)
                    if new_length <= max_allowed:
                        current_chunk.append(para)
                        chunks.append('\n\n'.join(current_chunk))
                        current_chunk = []
                        current_length = 0
                    else:
                        chunks.append('\n\n'.join(current_chunk))
                        current_chunk = [para]
                        current_length = para_length
            else:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_length = para_length
        
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        print(f"📦 Текст разбит на {len(chunks)} чанков")
        return chunks
