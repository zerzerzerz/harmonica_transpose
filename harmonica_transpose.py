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



# 调号相对于 C 调的半音偏移（以 C4 为 0）
# 假设标准 10 孔口琴调号顺序: G, Ab, A, Bb, B, C, Db, D, Eb, E, F, F#
# 所以 G 是最低的 (-5), F# 是最高的 (+6)
KEY_OFFSETS = {
    'G': -5, 'G#': -4, 'Ab': -4,
    'A': -3, 'A#': -2, 'Bb': -2,
    'B': -1,
    'C': 0, 'C#': 1, 'Db': 1,
    'D': 2, 'D#': 3, 'Eb': 3,
    'E': 4,
    'F': 5, 'F#': 6, 'Gb': 6
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


class Token:
    pass

class NoteToken(Token):
    def __init__(self, note_num: int, accidental: int, octave_offset: int):
        self.note_num = note_num
        self.accidental = accidental  # 0, 1 (#), -1 (b)
        self.octave_offset = octave_offset # -1, 0, 1, etc.

    def __repr__(self):
        return f"Note(num={self.note_num}, acc={self.accidental}, oct={self.octave_offset})"

class StrToken(Token):
    def __init__(self, text: str):
        self.text = text
    
    def __repr__(self):
        return f"Str({repr(self.text)})"


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


def parse_to_tokens(text: str) -> list[Token]:
    """
    解析文本为 Token 列表，同时计算八度偏移
    """
    text = normalize_brackets(text)
    tokens = []
    i = 0
    n = len(text)
    
    # helper to find matching closing bracket
    def find_closing(start_index, open_char, close_char):
        balance = 1
        j = start_index + 1
        while j < n:
            if text[j] == open_char:
                balance += 1
            elif text[j] == close_char:
                balance -= 1
                if balance == 0:
                    return j
            j += 1
        return -1

    # 可接受的非音符字符
    acceptable_chars = set(' \t\n\r0890=-|/\\:;,.!?=_')

    def parse_segment(segment_text, current_octave_offset):
        local_tokens = []
        k = 0
        m = len(segment_text)
        
        while k < m:
            char = segment_text[k]
            
            # 递归处理 ()
            if char == '(':
                closing_idx = -1
                balance = 1
                l = k + 1
                while l < m:
                    if segment_text[l] == '(':
                        balance += 1
                    elif segment_text[l] == ')':
                        balance -= 1
                        if balance == 0:
                            closing_idx = l
                            break
                    l += 1
                
                if closing_idx != -1:
                    inner_text = segment_text[k+1:closing_idx]
                    local_tokens.extend(parse_segment(inner_text, current_octave_offset - 1))
                    k = closing_idx + 1
                    continue
                else:
                     local_tokens.append(StrToken(char))
                     k += 1
                     continue

            # 递归处理 []
            if char == '[':
                closing_idx = -1
                balance = 1
                l = k + 1
                while l < m:
                    if segment_text[l] == '[':
                        balance += 1
                    elif segment_text[l] == ']':
                        balance -= 1
                        if balance == 0:
                            closing_idx = l
                            break
                    l += 1
                
                if closing_idx != -1:
                    inner_text = segment_text[k+1:closing_idx]
                    local_tokens.extend(parse_segment(inner_text, current_octave_offset + 1))
                    k = closing_idx + 1
                    continue
                else:
                    local_tokens.append(StrToken(char))
                    k += 1
                    continue

            # 处理音符
            accidental = 0
            note_found = False
            
            # 检查升降号
            temp_k = k
            if char == '#':
                accidental = 1
                temp_k += 1
            elif char in 'b♭':
                accidental = -1
                temp_k += 1
            
            if temp_k < m and segment_text[temp_k].isdigit() and segment_text[temp_k] in '1234567':
                note_num = int(segment_text[temp_k])
                local_tokens.append(NoteToken(note_num, accidental, current_octave_offset))
                k = temp_k + 1
                note_found = True
            
            if not note_found:
                 # if we consumed an accidental but didn't find a number, back up? 
                 # actually if we saw # but no number, treat # as string
                 if accidental != 0:
                     local_tokens.append(StrToken(char)) # original char
                     k += 1
                 elif char.isdigit() and char in '1234567':
                     # Handled above
                     pass
                 else:
                     # Plain text
                     local_tokens.append(StrToken(char))
                     k += 1
        
        return local_tokens

    return parse_segment(text, 0)


def transpose_tokens(tokens: list[Token], source_key: str, target_key: str) -> list[Token]:
    source_offset = KEY_OFFSETS.get(source_key.capitalize(), 0)
    target_offset = KEY_OFFSETS.get(target_key.capitalize(), 0)
    
    new_tokens = []
    
    for token in tokens:
        if isinstance(token, NoteToken):
            # Calculate absolute pitch (0 = Middle C)
            # base semitone (0-11) + accidental + key_offset + octave * 12
            original_semitone = NOTE_SEMITONES[token.note_num] + token.accidental
            absolute_pitch = original_semitone + source_offset + (token.octave_offset * 12)
            
            # Convert to target key coordinates
            # Target pitch = absolute pitch
            # Relative semitone in target key = absolute pitch - target_offset
            target_relative_pitch = absolute_pitch - target_offset
            
            # Normalize to note + octave
            # Python's % operator handles negatives correctly for modulo (e.g. -1 % 12 = 11)
            # // operator floors (e.g. -1 // 12 = -1)
            new_note_semitone_val = target_relative_pitch % 12
            new_octave = target_relative_pitch // 12
            
            new_note_str, new_acc_str = SEMITONE_TO_NOTE[new_note_semitone_val]
            new_note_num = int(new_note_str)
            new_acc = 1 if new_acc_str == '#' else 0 # simplistic, assuming only # output for now from map
            
            new_tokens.append(NoteToken(new_note_num, new_acc, new_octave))
        else:
            new_tokens.append(token)
            
    return new_tokens


def render_tokens(tokens: list[Token]) -> str:
    result = []
    for token in tokens:
        if isinstance(token, StrToken):
            result.append(token.text)
        elif isinstance(token, NoteToken):
            # Render accidental
            acc_str = '#' if token.accidental == 1 else ('b' if token.accidental == -1 else '')
            note_str = f"{acc_str}{token.note_num}"
            
            # Wrap octaves
            # < 0: ( ... )
            # > 0: [ ... ]
            prefix = ""
            suffix = ""
            
            if token.octave_offset < 0:
                count = abs(token.octave_offset)
                prefix = "(" * count
                suffix = ")" * count
            elif token.octave_offset > 0:
                count = token.octave_offset
                prefix = "[" * count
                suffix = "]" * count
            
            result.append(f"{prefix}{note_str}{suffix}")
            
    return "".join(result)


def transpose_sheet(text: str, target_key: str, source_key: str = 'C') -> tuple[str, list[str]]:
    """
    转调整个谱子
    """
    # 1. Parsing
    try:
        tokens = parse_to_tokens(text)
    except Exception as e:
        return f"Parsing Error: {e}", [str(e)]

    # 2. Transposition
    transposed_tokens = transpose_tokens(tokens, source_key, target_key)
    
    # 3. Rendering
    result_text = render_tokens(transposed_tokens)
    
    # Collect warnings (deprecated logic, but keeping interface)
    warnings = [] 
    
    return result_text, warnings



def main():
    parser = argparse.ArgumentParser(description="口琴谱调号转换程序")
    parser.add_argument("--input", "-i", help="输入文件路径", default="input")
    parser.add_argument("--output", "-o", help="输出文件路径", default="output")
    parser.add_argument("--target", "-t", help="目标调号 (例如: D, G, C#)", default="D")
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
