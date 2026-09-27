# -*- coding: utf-8 -*-
"""Convert ggg斗罗同人文.md to LaTeX (XeLaTeX / ctexart)."""
import re

SRC = r'g:\4\ord\小说\gggDouluo\ggg斗罗同人文.md'
DST = r'g:\4\ord\小说\gggDouluo\ggg斗罗同人文.tex'

# ---------------------------------------------------------------- unicode -> latex math
UNI = {
    # Greek
    'ω': r'\omega', 'ε': r'\varepsilon', 'ζ': r'\zeta', 'φ': r'\varphi',
    'α': r'\alpha', 'β': r'\beta', 'ψ': r'\psi', 'η': r'\eta',
    'Ω': r'\Omega', 'Π': r'\Pi', 'Γ': r'\Gamma',
    # subscripts
    '₀': '_{0}', '₁': '_{1}', '₂': '_{2}', '₃': '_{3}', '₄': '_{4}',
    '₅': '_{5}', '₆': '_{6}', '₇': '_{7}', '₈': '_{8}', '₉': '_{9}',
    '₊': '_{+}', '₋': '_{-}', 'ₙ': '_{n}', 'ₘ': '_{m}', 'ₖ': '_{k}',
    # superscripts
    '⁰': '^{0}', '¹': '^{1}', '²': '^{2}', '³': '^{3}', '⁴': '^{4}',
    '⁵': '^{5}', '⁶': '^{6}', '⁷': '^{7}', '⁸': '^{8}', '⁹': '^{9}',
    'ⁿ': '^{n}', 'ᵐ': '^{m}', 'ᶜ': '^{c}', 'ᵇ': '^{b}', 'ᴳ': '^{G}',
    '⁺': '^{+}', '⁻': '^{-}', '⁽': '^{(}', '⁾': '^{)}',
    # operators / relations / arrows
    '↑': r'\uparrow', '→': r'\rightarrow', '↦': r'\mapsto',
    '×': r'\times', '−': '-', '∼': r'\sim', '≠': r'\neq',
    '∞': r'\infty', '∩': r'\cap', '∅': r'\varnothing',
    '⋯': r'\cdots', '′': r'\prime', 'ℤ': r'\mathbb{Z}',
}
SUBSUP = ''.join(c for c in UNI if c in '₀₁₂₃₄₅₆₇₈₉₊₋ₙₘₖ⁰¹²³⁴⁵⁶⁷⁸⁹ⁿᵐᶜᵇᴳ⁺⁻⁽⁾')

SUP_MAP = {'⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4', '⁵': '5',
           '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9', 'ⁿ': 'n', 'ᵐ': 'm',
           'ᶜ': 'c', 'ᵇ': 'b', 'ᴳ': 'G', '⁺': '+', '⁻': '-',
           '⁽': '(', '⁾': ')'}
SUB_MAP = {'₀': '0', '₁': '1', '₂': '2', '₃': '3', '₄': '4', '₅': '5',
           '₆': '6', '₇': '7', '₈': '8', '₉': '9', '₊': '+', '₋': '-',
           'ₙ': 'n', 'ₘ': 'm', 'ₖ': 'k'}


def is_wrap(c):
    """CJK / CJK punctuation: must sit in \\text{} when inside math mode."""
    o = ord(c)
    return ((0x4E00 <= o <= 0x9FFF) or (0x3400 <= o <= 0x4DBF)
            or (0xF900 <= o <= 0xFAFF) or (0x3000 <= o <= 0x303F)
            or (0xFF00 <= o <= 0xFFEF) or c in '—…“”‘’·')


TEXT_MACRO = re.compile(r'\\(?:text|textbf|textrm|mathrm|operatorname|mathcal)\s*\{')


def math_to_latex(txt):
    """Convert a math chunk: unicode -> commands, stacked sub/superscripts merge,
    CJK -> \\text{}, existing \\text{..} groups left untouched."""
    out, i, n = [], 0, len(txt)
    while i < n:
        c = txt[i]
        m = TEXT_MACRO.match(txt, i)
        if m:
            k, depth = m.end() - 1, 0
            while k < n:
                if txt[k] == '{':
                    depth += 1
                elif txt[k] == '}':
                    depth -= 1
                    if depth == 0:
                        break
                k += 1
            out.append(txt[i:k + 1])
            i = k + 1
            continue
        if c == '\\' and i + 1 < n and txt[i + 1] in r'_&%$#{}':
            out.append(txt[i:i + 2])             # already escaped in the source
            i += 2
            continue
        if is_wrap(c):
            j = i
            while j < n and is_wrap(txt[j]):
                j += 1
            out.append('\\text{' + txt[i:j] + '}')
            i = j
            continue
        done = False
        for op, table in (('^', SUP_MAP), ('_', SUB_MAP)):
            if c in table:
                j = i
                while j < n and txt[j] in table:
                    j += 1
                out.append('%s{%s}' % (op, ''.join(table[txt[k]] for k in range(i, j))))
                i, done = j, True
                break
        if done:
            continue
        if c == '#' or c == '%':
            DIAG.append('bare %r in math' % c)
            out.append('\\' + c)
            i += 1
            continue
        out.append(c if (c.isascii() or c in '_^') else UNI.get(c, c))
        i += 1
    return ''.join(out)


MATRIX_RE = re.compile(r'\\begin\{(pmatrix|bmatrix|vmatrix|matrix)\}(.*?)\\end\{\1\}', re.S)
MATRIX_DELIM = {'pmatrix': (r'\left(', r'\right)'), 'bmatrix': (r'\left[', r'\right]'),
                'vmatrix': (r'\left|', r'\right|'), 'matrix': ('', '')}


def fix_matrices(body):
    """Rows of a matrix env may have unequal column counts -> use array with max cols."""
    def repl(m):
        env, inner = m.group(1), m.group(2)
        ncol = max((r.count('&') + 1 for r in re.split(r'\\\\', inner)), default=1)
        left, right = MATRIX_DELIM[env]
        return '%s\\begin{array}{%s}%s\\end{array}%s' % (left, 'c' * ncol, inner, right)
    return MATRIX_RE.sub(repl, body)


TEXT_ESC = {'&': r'\&', '%': r'\%', '#': r'\#', '_': r'\_', '{': r'\{',
            '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}',
            '<': r'\textless{}', '>': r'\textgreater{}'}
CODE_ESC = dict(TEXT_ESC)
CODE_ESC['\\'] = r'\textbackslash{}'
CODE_ESC['$'] = r'\$'

DIAG = []


class Tok:
    """Inline markdown -> LaTeX, state-aware (math may span lines)."""

    def __init__(self):
        self.math = False
        self.bold = False

    def run(self, s, blocks):
        out = []
        i, n = 0, len(s)
        while i < n:
            c = s[i]
            if c == '\x02':                      # display-math placeholder
                j = s.index('\x02', i + 1)
                out.append(blocks[int(s[i + 1:j])])
                i = j + 1
                continue
            if c == '$':                         # inline math toggle
                out.append('$')
                self.math = not self.math
                i += 1
                continue
            if self.math:
                m = re.search(r'(?<!\\)\$', s[i:])
                if m:
                    out.append(math_to_latex(s[i:i + m.start()]))
                    out.append('$')
                    self.math = False
                    i += m.start() + 1
                else:                            # math continues on the next line
                    out.append(math_to_latex(s[i:]))
                    i = n
                continue
            # ---- text mode
            if c == '`':                         # inline code
                j = s.find('`', i + 1)
                if j == -1:
                    out.append('`')
                    i += 1
                    continue
                out.append(r'\texttt{' + ''.join(CODE_ESC.get(ch, ch) for ch in s[i + 1:j]) + '}')
                i = j + 1
                continue
            if s.startswith('**', i):            # bold
                out.append(r'\textbf{' if not self.bold else '}')
                self.bold = not self.bold
                i += 2
                continue
            if s.startswith('&nbsp;', i):
                out.append('~')
                i += 6
                continue
            if c in UNI:                         # unicode math run (+ absorption)
                j = i
                while j < n and s[j] in UNI:
                    j += 1
                start, end = i, j
                m = re.search(r'[A-Za-z0-9]+$', s[:start])
                if m and m.start() > 0:
                    bpos = m.start() - 1
                    if s[bpos] in '_^':
                        if bpos == 0 or s[bpos - 1] != '\\':
                            start = m.start()        # f_ω₊₁ -> $f_{\omega_{+1}}$
                    elif s[start] in SUBSUP and s[bpos] != '\\':
                        start = m.start()            # 2²⁴ -> $2^{24}$
                m2 = re.match(r'[_^][A-Za-z0-9]+', s[end:])
                if m2:
                    end += m2.end()              # ε_0 -> $\varepsilon_0$
                tok = s[start:end]
                out.append('$' + math_to_latex(tok) + '$')
                i = end
                continue
            if c == '\\' and i + 1 < n and s[i + 1] in r'_&%$#{}':
                out.append(s[i:i + 2])           # already escaped in the source
                i += 2
                continue
            out.append(TEXT_ESC.get(c, c))
            i += 1
        return ''.join(out)


def disp_env(body):
    if re.search(r'\\begin\{(align|gather|multline|eqnarray|flalign)\*?\}', body):
        return body
    if '\\tag' in body:
        return '\\begin{equation*}\n' + body + '\n\\end{equation*}'
    return '\\[\n' + body + '\n\\]'


def conv_table(rows, tok):
    grid = []
    for r in rows:
        cells = [x.strip() for x in r.strip().strip('|').split('|')]
        if all(re.fullmatch(r':?-{1,}:?', x) for x in cells if x != ''):
            continue
        grid.append(cells)
    ncol = max(len(r) for r in grid)
    spec = '|' + 'X|' * ncol
    out = [r'\begin{center}', r'\begin{tabularx}{\textwidth}{%s}' % spec, r'\hline']
    for r in grid:
        cells = (r + [''] * ncol)[:ncol]
        out.append(' & '.join(tok.run(c, []).strip() for c in cells) + r' \\ \hline')
    out += [r'\end{tabularx}', r'\end{center}']
    return out


def main():
    raw = open(SRC, encoding='utf-8').read()
    # repair the one corrupted spot (U+FFFD)
    raw = re.sub('\ufffd+况', '情况', raw)
    raw = raw.replace('\ufffd', '')
    # repair the single unclosed inline-math delimiter in the source
    raw = raw.replace('$a_{41}=0。', '$a_{41}=0$。')
    # \th (thorn) is invalid in math mode; the author meant the "n-th" suffix
    raw = re.sub(r'\\th(?![A-Za-z])', r'\\text{th}', raw)

    # hoist every $$..$$ display block into a single-line placeholder
    blocks = []

    def grab(m):
        body = m.group(1)
        if '$' in body:
            DIAG.append('display match contains $: ' + body[:60].replace('\n', ' '))
        # sanity: top-level & or \\ inside a display block would break \[..\]
        depth, k = 0, 0
        while k < len(body):
            m2 = re.match(r'\\(begin|end)\{', body[k:])
            if m2:
                depth += 1 if m2.group(1) == 'begin' else -1
                k += m2.end()
                continue
            if depth == 0 and body[k] in '&%':
                DIAG.append('display block has top-level %r' % body[k])
            k += 1
        blocks.append(disp_env(fix_matrices(math_to_latex(body).strip())))
        return '\x02%d\x02' % (len(blocks) - 1)

    doc = re.sub(r'\$\$(.+?)\$\$', grab, raw, flags=re.S)
    if doc.count('$') % 2:
        raise SystemExit('unbalanced inline $ after display hoisting')
    lines = doc.split('\n')

    idx0 = next(i for i, l in enumerate(lines) if re.match(r'^#{1,6}\s', l))

    res = []
    tok = Tok()
    state = {'quote': False, 'list': None, 'tbl': [], 'fence': False}

    def close_all():
        if state['tbl']:
            res.extend(conv_table(state['tbl'], tok))
            res.append('')
            state['tbl'] = []
        if state['quote']:
            res.append(r'\end{quote}')
            res.append('')
            state['quote'] = False
        if state['list']:
            res.append(r'\end{%s}' % state['list'])
            res.append('')
            state['list'] = None

    for line in lines[idx0:]:
        if re.match(r'^\s*```', line):
            close_all()
            if state['fence']:
                res.append(r'\end{lstlisting}')
                res.append('')
            else:
                res.append(r'\begin{lstlisting}')
            state['fence'] = not state['fence']
            continue
        if state['fence']:
            res.append(line)
            continue

        stripped = line.strip()
        if stripped.startswith('|'):
            if state['quote'] or state['list']:
                close_all()
            state['tbl'].append(line)
            continue
        if state['tbl']:
            res.extend(conv_table(state['tbl'], tok))
            res.append('')
            state['tbl'] = []

        if re.match(r'^#{1,6}\s', line):
            close_all()
            title = re.sub(r'^#{1,6}\s*', '', line).strip()
            res.append('')
            res.append(r'\section{' + tok.run(title, blocks) + '}')
            continue
        if re.match(r'^>', line):
            if state['list']:
                close_all()
            if not state['quote']:
                res.append('')
                res.append(r'\begin{quote}')
                state['quote'] = True
            body = re.sub(r'^>\s?', '', line)
            res.append(tok.run(body, blocks))
            continue
        m = re.match(r'^(\s*)([-*+]|\d+\.)\s+(.*)$', line)
        if m:
            if state['quote']:
                close_all()
            want = 'enumerate' if m.group(2)[0].isdigit() else 'itemize'
            if state['list'] and m.group(1):
                pass                      # flattened: keep same list
            elif state['list'] and state['list'] != want:
                close_all()
            if not state['list']:
                res.append('')
                res.append(r'\begin{%s}' % want)
                state['list'] = want
            res.append(r'\item ' + tok.run(m.group(3), blocks))
            continue
        if re.match(r'^-{3,}\s*$', stripped):
            close_all()
            res.append('')
            res.append(r'\begin{center}\rule{6em}{0.4pt}\end{center}')
            continue
        if stripped == '':
            close_all()
            if res and res[-1] != '':
                res.append('')
            continue
        close_all()
        res.append(tok.run(line, blocks))

    close_all()

    preamble = r'''\documentclass[UTF8]{ctexart}
\usepackage{amsmath,amssymb}
\usepackage{xcolor}
\usepackage{listings}
\usepackage{tabularx}
\setcounter{secnumdepth}{0}
\renewcommand{\contentsname}{目录}
\setCJKmonofont{SimSun}
\lstset{basicstyle=\ttfamily\small,breaklines=true,columns=flexible,frame=single,extendedchars=false}
\title{ggg斗罗同人文}
\author{SmliceGreen}
\begin{document}
\maketitle
\tableofcontents
\newpage
'''
    body = '\n'.join(res)
    body = re.sub(r'\n{3,}', '\n\n', body)
    open(DST, 'w', encoding='utf-8').write(preamble + body + '\n\\end{document}\n')

    print('blocks:', len(blocks), 'lines out:', body.count('\n'))
    leftover = sorted({c for c in body if ord(c) > 127 and not (0x4E00 <= ord(c) <= 0x9FFF)
                       and not (0x3000 <= ord(c) <= 0x303F) and not (0xFF00 <= ord(c) <= 0xFFEF)
                       and c not in '—…“”‘’·üé'})
    print('leftover non-ascii (unmapped):', [(hex(ord(c)), c) for c in leftover])
    for d in DIAG[:20]:
        print('DIAG:', d)
    print('DIAG count:', len(DIAG))


main()