#!/usr/bin/env python3
"""
口琴谱调号转换程序

符号说明：
- #1 表示升半音
- b1 表示降半音
- (1) 或 （1） 表示低八度
- [1] 或 【1】 表示高八度
- 数字 1-7 表示音阶中的音符

使用方法：
    python harmonica_transpose.py input.txt D  # 将 input.txt 中的谱子从 C 调转到 D 调
    python harmonica_transpose.py input.txt G  # 将 input.txt 中的谱子从 C 调转到 G 调
"""

import argparse
import sys
from typing import Tuple


# 半音数量映射（以 C 为基准）
KEY_SEMITONES = {
    'C': 0, 'C#': 1, 'Db': 1,
    'D': 2, 'D#': 3, 'Eb': 3,
    'E': 4,
    'F': 5, 'F#': 6, 'Gb': 6,
    'G': 7, 'G#': 8, 'Ab': 8,
    'A': 9, 'A#': 10, 'Bb': 10,
    'B': 11
}

# 音符对应的半音数（相对于 C 大调）
# 1=C, 2=D, 3=E, 4=F, 5=G, 6=A, 7=B
NOTE_SEMITONES = {
    1: 0,   # C
    2: 2,   # D
    3: 4,   # E
    4: 5,   # F
    5: 7,   # G
    6: 9,   # A
    7: 11   # B
}

# 半音到音符的反向映射
SEMITONE_TO_NOTE = {
    0: ('1', ''),    # C
    1: ('1', '#'),   # C#
    2: ('2', ''),    # D
    3: ('2', '#'),   # D#
    4: ('3', ''),    # E
    5: ('4', ''),    # F
    6: ('4', '#'),   # F#
    7: ('5', ''),    # G
    8: ('5', '#'),   # G#
    9: ('6', ''),    # A
    10: ('6', '#'),  # A#
    11: ('7', ''),   # B
}


def semitone_to_note_str(semitone: int) -> str:
    """
    将半音数转换为音符字符串
    """
    semitone = semitone % 12
    note, accidental = SEMITONE_TO_NOTE[semitone]
    return accidental + note


def transpose_note(note_num: int, accidental: int, semitone_shift: int) -> str:
    """
    转调单个音符
    note_num: 1-7 的音符
    accidental: 升降号 (0, 1, -1)
    semitone_shift: 半音位移量
    返回: 转调后的音符字符串（如 "#2", "5", "b3"）
    """
    if note_num < 1 or note_num > 7:
        return str(note_num)
    
    # 计算原始音符的半音位置
    original_semitone = NOTE_SEMITONES[note_num] + accidental
    
    # 转调
    new_semitone = (original_semitone + semitone_shift) % 12
    
    return semitone_to_note_str(new_semitone)


def normalize_brackets(text: str) -> str:
    """
    将中文字符的括号替换为英文字符的括号
    """
    replacements = {
        '（': '(',
        '）': ')',
        '【': '[',
        '】': ']'
    }
    for cn, en in replacements.items():
        text = text.replace(cn, en)
    return text


def transpose_sheet(text: str, target_key: str, source_key: str = 'C') -> tuple[str, list[str]]:
    """
    转调整个谱子
    返回: (转调后的谱子，警告列表)
    """
    # 统一替换为英文括号
    text = normalize_brackets(text)
    
    # 计算半音位移
    source_semitones = KEY_SEMITONES.get(source_key.capitalize(), 0)
    target_semitones = KEY_SEMITONES.get(target_key.capitalize(), 0)
    semitone_shift = source_semitones - target_semitones
    
    result = []
    warnings = []
    i = 0
    
    # 定义可接受的非音符字符
    acceptable_chars = set(' \t\n\r0890=-|/\\:;,.!?=_')
    
    while i < len(text):
        char = text[i]
        
        # 处理低八度标记 () 
        if char == '(':
            j = i + 1
            inner_content = []
            
            while j < len(text) and text[j] != ')':
                inner_content.append(text[j])
                j += 1
            
            if j < len(text):
                # 递归处理括号内的内容
                inner_text = ''.join(inner_content)
                transposed_inner, inner_warnings = transpose_sheet(inner_text, target_key, source_key)
                warnings.extend(inner_warnings)
                result.append('(')
                result.append(transposed_inner)
                result.append(')')
                i = j + 1
            else:
                result.append(char)
                i += 1
            continue
        
        # 处理高八度标记 []
        if char == '[':
            j = i + 1
            inner_content = []
            
            while j < len(text) and text[j] != ']':
                inner_content.append(text[j])
                j += 1
            
            if j < len(text):
                inner_text = ''.join(inner_content)
                transposed_inner, inner_warnings = transpose_sheet(inner_text, target_key, source_key)
                warnings.extend(inner_warnings)
                result.append('[')
                result.append(transposed_inner)
                result.append(']')
                i = j + 1
            else:
                result.append(char)
                i += 1
            continue
        
        # 处理升号 #
        if char == '#':
            # 检查后面是否有数字
            if i + 1 < len(text) and text[i + 1].isdigit():
                note_num = int(text[i + 1])
                transposed = transpose_note(note_num, 1, semitone_shift)
                result.append(transposed)
                i += 2
                continue
        
        # 处理降号 b 或 ♭
        if char in 'b♭':
            # 检查后面是否有数字
            if i + 1 < len(text) and text[i + 1].isdigit():
                note_num = int(text[i + 1])
                transposed = transpose_note(note_num, -1, semitone_shift)
                result.append(transposed)
                i += 2
                continue
        
        # 处理普通音符数字 1-7
        if char.isdigit() and char in '1234567':
            note_num = int(char)
            transposed = transpose_note(note_num, 0, semitone_shift)
            result.append(transposed)
            i += 1
            continue
        
        # 其他字符
        if char in acceptable_chars:
            result.append(char)
        else:
            # 未知字符，发出警告但仍保留
            if char not in [c for c, _ in warnings]:
                warnings.append((char, i))
            result.append(char)
        i += 1
    
    return ''.join(result), warnings


def main():
    parser = argparse.ArgumentParser(description="口琴谱调号转换程序")
    parser.add_argument("--input", "-i", help="输入文件路径", default="input")
    parser.add_argument("--output", "-o", help="输出文件路径", default="output")
    parser.add_argument("--target", help="目标调号 (例如: D, G, C#)", default="D")
    parser.add_argument("--source", "-s", default="C", help="源调号 (默认: C)")
    parser.add_argument("--warnings", "-w", help="警告信息输出文件路径", default="warnings")
    
    args = parser.parse_args()
    
    input_arg = args.input
    target_key = args.target
    source_key = args.source
    
    if not input_arg:
        print("错误: 请通过 --input 或 -i 指定输入文件路径或谱子内容。")
        return
        
    if not target_key:
        print("错误: 请通过 --target 指定目标调号。")
        return
    
    # 尝试读取文件
    try:
        with open(input_arg, 'r', encoding='utf-8') as f:
            sheet_content = f.read()
    except (FileNotFoundError, OSError, TypeError):
        # 如果不是文件，就当作谱子内容处理
        sheet_content = input_arg
    
    # 转调
    result, warnings = transpose_sheet(sheet_content, target_key, source_key)
    
    # 构建警告文本
    warning_text = ""
    if warnings:
        warning_lines = ["警告: 以下字符无法识别为音符，已原样保留:"]
        unique_chars = sorted(set(c for c, _ in warnings))
        for char in unique_chars:
            warning_lines.append(f"  '{char}' (Unicode: U+{ord(char):04X})")
        warning_text = "\n".join(warning_lines) + "\n"

    # 输出警告
    if warning_text:
        if args.warnings:
            try:
                with open(args.warnings, 'w', encoding='utf-8') as f:
                    f.write(warning_text)
                print(f"警告信息已成功保存到: {args.warnings}")
            except Exception as e:
                print(f"错误: 无法写入警告文件 {args.warnings}: {e}")
                print(warning_text)
        else:
            print(warning_text)
    
    header = f"=== 从 {source_key.upper()} 调转换到 {target_key.upper()} 调 ===\n"
    output_text = header + result
    
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_text)
            print(f"转换结果已成功保存到: {args.output}")
        except Exception as e:
            print(f"错误: 无法写入输出文件 {args.output}: {e}")
    else:
        print(output_text)


if __name__ == '__main__':
    main()
