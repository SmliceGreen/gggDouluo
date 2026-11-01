#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tex2md.py — 把 ggg斗罗同人文.tex 逆转换回 ggg斗罗同人文.md
针对上游 ChatGPT 转换产物的自定义宏做剥壳处理：
  \\NovelInline{ID}{X}   -> $X$
  \\NovelDisplay{ID}{X}  -> $$X$$
  \\allowbreak{}         -> (删除)
  \\chapter{T}           -> # T
  \\textbf{X}            -> **X**
  \\textcolor[HTML]{c}{X}-> 原样保留(pandoc 透传)
  \\begin{quote}...\\end{quote}  -> > ...
  itemize/enumerate      -> 列表
  LaTeX 转义符还原
"""
import re
import sys

def find_matching_brace(text, start):
    """从 text[start]=='{' 开始找匹配的 '}'，处理嵌套和转义。返回 '}' 的索引。"""
    depth = 0
    i = start
    while i < len(text):
        c = text[i]
        if c == '\\':
            i += 2  # 跳过转义字符
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1

def extract_brace_arg(text, pos):
    """提取 pos 处 '{' 开始的花括号参数内容，返回 (内容, 结束索引+1)。"""
    assert text[pos] == '{'
    end = find_matching_brace(text, pos)
    return text[pos+1:end], end+1

def strip_trailing_percent(body):
    """去掉每行末尾的 % (LaTeX 行连接符)。"""
    lines = body.split('\n')
    out = []
    for l in lines:
        # 去掉行尾 % 及前面的可选空格
        l = re.sub(r'\s*%\s*$', '', l)
        out.append(l)
    return '\n'.join(out)

def process_inline_macros(line):
    """处理一行内的内联宏：\\NovelInline, \\allowbreak{}, \\textbf, \\textcolor 等。"""
    result = []
    i = 0
    n = len(line)
    while i < n:
        c = line[i]
        if c != '\\':
            result.append(c)
            i += 1
            continue
        # 反斜杠开头，尝试匹配宏名
        m = re.match(r'\\([a-zA-Z]+)', line[i:])
        if not m:
            # 不是字母宏，可能是 \\# \\& 等转义
            if i+1 < n and line[i+1] in '#&%_':
                result.append(line[i+1])  # 还原转义
                i += 2
            elif i+1 < n and line[i+1] == ' ':
                result.append(' ')  # \ 空格 -> 空格
                i += 2
            elif i+1 < n and line[i+1] == '\\':
                result.append('\n')  # \\ -> 换行
                i += 2
            else:
                result.append(line[i])
                i += 1
            continue
        macro = m.group(1)
        j = i + len(m.group(0))  # 宏名后的位置
        # 跳过可选的 [选项]
        k = j
        if k < n and line[k] == '[':
            depth = 0
            while k < n:
                if line[k] == '[':
                    depth += 1
                elif line[k] == ']':
                    depth -= 1
                    if depth == 0:
                        k += 1
                        break
                k += 1
        if macro == 'allowbreak':
            # \allowbreak{} — 删除
            # 跳过可能的 {}
            if k < n and line[k] == '{':
                _, k = extract_brace_arg(line, k)
            i = k
            continue
        if macro == 'NovelInline':
            # \NovelInline{ID}{content} -> $content$
            if k < n and line[k] == '{':
                _, k = extract_brace_arg(line, k)  # ID
            if k < n and line[k] == '{':
                content, k = extract_brace_arg(line, k)
                result.append('$' + content + '$')
            i = k
            continue
        if macro == 'textbf':
            if k < n and line[k] == '{':
                content, k = extract_brace_arg(line, k)
                result.append('**' + content + '**')
                i = k
                continue
        if macro == 'textcolor':
            # \textcolor[HTML]{color}{content} -> 保留原样
            # 收集原始文本
            raw = line[i:k]
            if k < n and line[k] == '{':
                _, k2 = extract_brace_arg(line, k)
                raw += line[k:k2]
                k = k2
            if k < n and line[k] == '{':
                _, k2 = extract_brace_arg(line, k)
                raw += line[k:k2]
                k = k2
            result.append(raw)
            i = k
            continue
        if macro == 'label':
            if k < n and line[k] == '{':
                _, k = extract_brace_arg(line, k)
            i = k
            continue
        if macro == 'par':
            result.append('\n')
            i = k
            continue
        # 未知宏：保留原样
        result.append(line[i:k])
        i = k
    return ''.join(result)

def process_display_math(body):
    """处理 \\NovelDisplay{ID}{content} -> $$content$$。content 可能跨行。"""
    out = []
    i = 0
    n = len(body)
    while i < n:
        if body[i:i+13] == '\\NovelDisplay':
            j = i + 13
            # 跳过 {ID}
            if j < n and body[j] == '{':
                _, j = extract_brace_arg(body, j)
            # 跳过 {content}
            if j < n and body[j] == '{':
                content, j = extract_brace_arg(body, j)
                content = strip_trailing_percent(content)
                content = content.strip()
                out.append('$$\n' + content + '\n$$')
            i = j
        else:
            out.append(body[i])
            i += 1
    return ''.join(out)

def process_quotes(body):
    """\\begin{quote}...\\end{quote} -> 每行加 '> '。"""
    def repl(m):
        inner = m.group(1).strip()
        lines = inner.split('\n')
        return '\n'.join('> ' + l if l.strip() else '>' for l in lines)
    return re.sub(r'\\begin\{quote\}(.*?)\\end\{quote\}', repl, body, flags=re.S)

def process_itemize(body):
    """\\begin{itemize}...\\end{itemize} -> 无序列表。"""
    def repl(m):
        inner = m.group(1)
        items = re.split(r'\\item', inner)
        out = []
        for it in items:
            it = it.strip()
            if it:
                out.append('- ' + it)
        return '\n'.join(out)
    return re.sub(r'\\begin\{itemize\}(.*?)\\end\{itemize\}', repl, body, flags=re.S)

def process_enumerate(body):
    """\\begin{enumerate}...\\end{enumerate} -> 有序列表。"""
    def repl(m):
        inner = m.group(1)
        items = re.split(r'\\item', inner)
        out = []
        idx = 1
        for it in items:
            it = it.strip()
            if it:
                out.append(f'{idx}. ' + it)
                idx += 1
        return '\n'.join(out)
    return re.sub(r'\\begin\{enumerate\}(.*?)\\end\{enumerate\}', repl, body, flags=re.S)

def process_lstlisting(body):
    """\\begin{lstlisting}...\\end{lstlisting} -> ``` 代码块。"""
    def repl(m):
        return '```\n' + m.group(1).strip() + '\n```'
    return re.sub(r'\\begin\{lstlisting\}(.*?)\\end\{lstlisting\}', repl, body, flags=re.S)

def process_chapters(body):
    """\\chapter{T} -> # T。"""
    return re.sub(r'\\chapter\{([^}]*)\}', r'# \1', body)

def fix_dashes(body):
    """-- -> – (en-dash), --- -> — (em-dash)。注意 --- 要先处理。"""
    body = body.replace('---', '—')
    body = body.replace('--', '–')
    return body

def fix_tilde(body):
    """~ (不间断空格) -> 普通空格。"""
    return body.replace('~', ' ')

def remove_backmatter_tail(body):
    """截断 \backmatter 或 \end{document} 之后的内容。"""
    for marker in [r'\backmatter', r'\end{document}']:
        idx = body.find(marker)
        if idx >= 0:
            body = body[:idx]
    return body

def clean_multiple_blanklines(body):
    """3个以上空行压缩为2个。"""
    return re.sub(r'\n{3,}', '\n\n', body)

def tex_to_md(tex):
    # 取正文
    start = tex.find(r'\begin{document}')
    if start < 0:
        start = 0
    else:
        start += len(r'\begin{document}')
    body = tex[start:]
    body = remove_backmatter_tail(body)
    # 行间公式
    body = process_display_math(body)
    # 块环境
    body = process_quotes(body)
    body = process_itemize(body)
    body = process_enumerate(body)
    body = process_lstlisting(body)
    # 章节
    body = process_chapters(body)
    # 逐行处理内联宏
    lines = body.split('\n')
    lines = [process_inline_macros(l) for l in lines]
    body = '\n'.join(lines)
    # 标点和空格
    body = fix_dashes(body)
    body = fix_tilde(body)
    # 清理
    body = clean_multiple_blanklines(body)
    body = body.strip() + '\n'
    return body

if __name__ == '__main__':
    infile = sys.argv[1] if len(sys.argv) > 1 else 'ggg斗罗同人文.tex'
    outfile = sys.argv[2] if len(sys.argv) > 2 else 'ggg斗罗同人文.md'
    with open(infile, encoding='utf-8') as f:
        tex = f.read()
    md = tex_to_md(tex)
    with open(outfile, 'w', encoding='utf-8') as f:
        f.write(md)
    # 统计
    ch = len(re.findall(r'^# ', md, re.M))
    dm = len(re.findall(r'^\$\$', md, re.M))
    im = len(re.findall(r'(?<!\$)\$(?!\$)', md))
    print(f'chapters: {ch}')
    print(f'display math ($$): {dm}')
    print(f'inline math ($): {im}')
    print(f'output: {outfile}')
