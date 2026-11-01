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
            # 不是字母宏，保留原样
            # \# \& \% \_ 在文本和数学模式都合法，不还原
            if i+1 < n and line[i+1] == ' ':
                result.append(' ')  # \ 空格 -> 空格
                i += 2
            elif i+1 < n and line[i+1] == '\\':
                result.append('\\\\')  # 保留 \\（数学模式行分隔符，文本模式换行）
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
                content = process_inline_macros(content)  # 递归处理内部宏
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

_LIST_STOP = r'((?:(?!\\begin\{(?:itemize|enumerate)\}).)*?)'

def process_itemize(body):
    """\\begin{itemize}...\\end{itemize} -> 无序列表。支持嵌套（循环处理最内层）。"""
    def repl(m):
        inner = m.group(1)
        inner = re.sub(r'\\tightlist', '', inner)
        items = re.split(r'\\item', inner)
        out = []
        for it in items:
            it = it.strip()
            if it:
                out.append('- ' + it)
        return '\n'.join(out)
    pattern = r'\\begin\{itemize\}' + _LIST_STOP + r'\\end\{itemize\}'
    while True:
        new_body = re.sub(pattern, repl, body, flags=re.S)
        if new_body == body:
            break
        body = new_body
    return body

def process_enumerate(body):
    """\\begin{enumerate}...\\end{enumerate} -> 有序列表。支持嵌套。"""
    def repl(m):
        inner = m.group(1)
        inner = re.sub(r'\\tightlist', '', inner)
        items = re.split(r'\\item', inner)
        out = []
        idx = 1
        for it in items:
            it = it.strip()
            if it:
                out.append(f'{idx}. ' + it)
                idx += 1
        return '\n'.join(out)
    pattern = r'\\begin\{enumerate\}' + _LIST_STOP + r'\\end\{enumerate\}'
    while True:
        new_body = re.sub(pattern, repl, body, flags=re.S)
        if new_body == body:
            break
        body = new_body
    return body

def process_lstlisting(body):
    """\\begin{lstlisting}...\\end{lstlisting} -> ``` 代码块。"""
    def repl(m):
        return '```\n' + m.group(1).strip() + '\n```'
    return re.sub(r'\\begin\{lstlisting\}(.*?)\\end\{lstlisting\}', repl, body, flags=re.S)

def process_verbatim(body):
    """\\begin{verbatim}...\\end{verbatim} -> ``` 代码块。"""
    def repl(m):
        return '```\n' + m.group(1).strip() + '\n```'
    return re.sub(r'\\begin\{verbatim\}(.*?)\\end\{verbatim\}', repl, body, flags=re.S)

def process_longtable(body):
    """\\begin{longtable}...\\end{longtable} -> markdown 管道表格。"""
    def repl(m):
        inner = m.group(1).lstrip()
        # 去掉列规格：可选的 [...] 然后 {...}（可能含嵌套花括号，跨行）
        pos = 0
        if pos < len(inner) and inner[pos] == '[':
            depth = 0
            while pos < len(inner):
                if inner[pos] == '[': depth += 1
                elif inner[pos] == ']':
                    depth -= 1
                    if depth == 0:
                        pos += 1
                        break
                pos += 1
        if pos < len(inner) and inner[pos] == '{':
            _, pos = extract_brace_arg(inner, pos)
        inner = inner[pos:].lstrip('\n')
        # 去掉 minipage 包装
        inner = re.sub(r'\\begin\{minipage\}\[[^\]]*\]\{[^}]*\}(\\raggedright\s*)?', '', inner)
        inner = re.sub(r'\\end\{minipage\}', '', inner)
        # 去掉 \toprule \midrule \bottomrule \noalign \endhead \endlastfoot \caption \label
        inner = re.sub(r'\\(toprule|midrule|bottomrule)(\\noalign\{\})?', '', inner)
        inner = re.sub(r'\\(endhead|endlastfoot|endfirsthead)', '', inner)
        inner = re.sub(r'\\caption\{[^}]*\}', '', inner)
        inner = re.sub(r'\\label\{[^}]*\}', '', inner)
        # 按行处理，& 分隔
        lines = inner.split('\n')
        rows = []
        for l in lines:
            l = l.strip()
            if not l:
                continue
            # 去掉行尾 \\
            l = re.sub(r'\\\\\s*$', '', l)
            if not l.strip():
                continue
            cells = [c.strip() for c in l.split('&')]
            rows.append(cells)
        if not rows:
            return ''
        ncols = max(len(r) for r in rows)
        # 补齐列数
        rows = [r + [''] * (ncols - len(r)) for r in rows]
        out = []
        out.append('| ' + ' | '.join(rows[0]) + ' |')
        out.append('| ' + ' | '.join(['---'] * ncols) + ' |')
        for r in rows[1:]:
            out.append('| ' + ' | '.join(r) + ' |')
        return '\n'.join(out)
    return re.sub(r'\\begin\{longtable\}(.*?)\\end\{longtable\}', repl, body, flags=re.S)

def process_center(body):
    """\\begin{center}...\\end{center}：
    含 \\rule 的转为 ---（分隔线），否则保留内容。"""
    def repl(m):
        inner = m.group(1).strip()
        if '\\rule' in inner:
            return '---'
        return inner
    return re.sub(r'\\begin\{center\}(.*?)\\end\{center\}', repl, body, flags=re.S)

def process_minipage(body):
    """\\begin{minipage}...\\end{minipage} -> 保留内容。"""
    def repl(m):
        inner = re.sub(r'^\[[^\]]*\]\{[^}]*\}', '', m.group(1).strip())
        return inner
    return re.sub(r'\\begin\{minipage\}(.*?)\\end\{minipage\}', repl, body, flags=re.S)

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
    r"""截断 \backmatter 或 \end{document} 之后的内容。"""
    for marker in [r'\backmatter', r'\end{document}']:
        idx = body.find(marker)
        if idx >= 0:
            body = body[:idx]
    return body

def clean_multiple_blanklines(body):
    """3个以上空行压缩为2个。"""
    return re.sub(r'\n{3,}', '\n\n', body)

def clean_math_blanklines(body):
    """去掉 $$...$$ 显示数学块内的空行（LaTeX 数学模式不允许空行）。"""
    def repl(m):
        content = m.group(1)
        content = re.sub(r'\n{2,}', '\n', content)
        return '$$' + content + '$$'
    return re.sub(r'\$\$(.*?)\$\$', repl, body, flags=re.S)

def strip_structural_commands(body):
    """去掉应由 pandoc 模板处理的 LaTeX 结构命令：
    \\frontmatter, \\mainmatter, \\backmatter, \\tableofcontents,
    \\setcounter{tocdepth}, \\setstretch, \\appendix, \\pagestyle,
    \\pagenumbering，以及包裹它们的独立花括号行。"""
    lines = body.split('\n')
    out = []
    skip_brace = 0
    for l in lines:
        s = l.strip()
        # 独立的花括号行（包裹结构命令的分组）
        if s == '{' or s == '}':
            continue
        if re.match(r'\\(frontmatter|mainmatter|backmatter|appendix)\s*$', s):
            continue
        if re.match(r'\\tableofcontents\s*$', s):
            continue
        if re.match(r'\\setcounter\{tocdepth\}\{[^}]*\}\s*$', s):
            continue
        if re.match(r'\\setstretch\{[^}]*\}\s*$', s):
            continue
        if re.match(r'\\pagestyle\{[^}]*\}\s*$', s):
            continue
        if re.match(r'\\pagenumbering\{[^}]*\}\s*$', s):
            continue
        if re.match(r'\\listof(tables|figures)\s*$', s):
            continue
        out.append(l)
    return '\n'.join(out)

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
    body = process_verbatim(body)
    body = process_longtable(body)
    body = process_center(body)
    body = process_minipage(body)
    # 章节
    body = process_chapters(body)
    # 逐行处理内联宏
    lines = body.split('\n')
    lines = [process_inline_macros(l) for l in lines]
    body = '\n'.join(lines)
    # 去掉 LaTeX 结构命令
    body = strip_structural_commands(body)
    # 标点和空格
    body = fix_dashes(body)
    body = fix_tilde(body)
    # 清理 $$...$$ 块内的空行（LaTeX 数学模式不允许空行）
    body = clean_math_blanklines(body)
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
