#!/usr/bin/env python3
"""Convert the research programme overview notebook to LaTeX (LuaLaTeX-compatible)."""

import json
import re


def escape_text(s: str) -> str:
    """Escape LaTeX special chars in plain text, preserving math and LaTeX commands."""
    # Protect existing LaTeX math and commands
    protected = []
    counter = [0]

    def save(m):
        protected.append(m.group(0))
        idx = counter[0]
        counter[0] += 1
        return f'\x00PROT{idx}\x00'

    # Protect display math $$...$$
    s = re.sub(r'\$\$.*?\$\$', save, s, flags=re.DOTALL)
    # Protect inline math $...$ (must contain a backslash or common math chars to be real math)
    s = re.sub(r'\$(?=[^$]*[\\^_{}])[^$]+?\$', save, s)

    # Escape special chars in order that avoids double-escaping
    # 1. First handle &, %, # which have no interaction issues
    s = s.replace('&', r'\&')
    s = s.replace('%', r'\%')
    s = s.replace('#', r'\#')
    # 2. Escape literal $ (currency signs remaining after math protection)
    s = s.replace('$', r'\$')
    # 3. Underscores
    s = s.replace('_', r'\_')
    # 4. Tildes and carets
    s = s.replace('~', r'\textasciitilde{}')
    # Don't escape backslash or braces - they're very rare in text
    # and escaping them causes cascading issues

    # Unicode chars that might appear in text
    s = s.replace('−', '-')  # U+2212 minus sign
    s = s.replace('—', '---')
    s = s.replace('–', '--')
    s = s.replace(''', "'")
    s = s.replace(''', "'")
    s = s.replace('\u200b', '')  # zero-width space
    s = s.replace('≈', r'$\approx$')
    s = s.replace('≠', r'$\neq$')
    s = s.replace('≤', r'$\leq$')
    s = s.replace('≥', r'$\geq$')
    s = s.replace('×', r'$\times$')
    s = s.replace('→', r'$\rightarrow$')
    s = s.replace('←', r'$\leftarrow$')
    s = s.replace('↓', r'$\downarrow$')
    s = s.replace('↑', r'$\uparrow$')
    s = s.replace('∞', r'$\infty$')
    s = s.replace('Σ', r'$\Sigma$')
    s = s.replace('Δ', r'$\Delta$')
    s = s.replace('α', r'$\alpha$')
    s = s.replace('β', r'$\beta$')
    s = s.replace('γ', r'$\gamma$')
    s = s.replace('δ', r'$\delta$')
    s = s.replace('ε', r'$\varepsilon$')
    s = s.replace('λ', r'$\lambda$')
    s = s.replace('σ', r'$\sigma$')
    s = s.replace('τ', r'$\tau$')
    s = s.replace('π', r'$\pi$')
    s = s.replace('θ', r'$\theta$')
    s = s.replace('φ', r'$\varphi$')
    s = s.replace('ρ', r'$\rho$')
    s = s.replace('μ', r'$\mu$')
    s = s.replace('ν', r'$\nu$')
    s = s.replace('ω', r'$\omega$')
    s = s.replace('₁', r'$_1$')
    s = s.replace('₂', r'$_2$')
    s = s.replace('₃', r'$_3$')

    # Restore protected regions
    for i, p in enumerate(protected):
        s = s.replace(f'\x00PROT{i}\x00', p)

    return s


def process_inline(s: str) -> str:
    """Process inline markdown: bold, italic, code."""
    # Bold **text** or __text__
    s = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', s)
    s = re.sub(r'__(.+?)__', r'\\textbf{\1}', s)
    # Italic *text* (but not inside math $...$)
    # Simple approach: only match if not preceded/followed by $
    s = re.sub(r'(?<!\$)\*([^*\n]+?)\*(?!\$)', r'\\textit{\1}', s)
    # Inline code `text`
    s = re.sub(r'`([^`]+?)`', r'\\texttt{\1}', s)
    return s


def md_to_latex(md: str) -> str:
    """Convert markdown to LaTeX body."""
    lines = md.split('\n')
    out = []
    i = 0

    in_table = False
    table_rows = []
    in_code = False
    code_lines = []
    in_blockquote = False
    bq_lines = []
    in_itemize = False
    in_enumerate = False

    def flush_table():
        nonlocal table_rows, in_table
        if not table_rows:
            in_table = False
            return
        header = table_rows[0]
        data = table_rows[2:] if len(table_rows) > 2 else []
        cols = [c.strip() for c in header.split('|') if c.strip()]
        ncols = len(cols)
        if ncols == 0:
            table_rows = []
            in_table = False
            return

        # Use p{} columns for wide tables
        if ncols <= 3:
            col_spec = '|' + '|'.join(['l'] * ncols) + '|'
        elif ncols <= 5:
            widths = {2: '0.15\\textwidth', 3: '0.15\\textwidth',
                      4: '0.25\\textwidth', 5: '0.25\\textwidth'}
            first_w = '0.12\\textwidth'
            rest_w = f'{0.85/ncols:.2f}\\textwidth'
            col_spec = '|' + '|'.join([f'p{{{rest_w}}}'] * ncols) + '|'
        else:
            w = f'{0.90/ncols:.2f}\\textwidth'
            col_spec = '|' + '|'.join([f'p{{{w}}}'] * ncols) + '|'

        out.append('')
        out.append(r'{\small')
        out.append(r'\begin{longtable}{' + col_spec + '}')
        out.append(r'\hline')
        hdr_cells = [process_inline(escape_text(c.strip())) for c in cols]
        out.append(' & '.join([r'\textbf{' + c + '}' for c in hdr_cells]) + r' \\')
        out.append(r'\hline')
        out.append(r'\endhead')
        for row in data:
            cells = [c.strip() for c in row.split('|')]
            # Remove empty first/last from leading/trailing |
            if cells and cells[0] == '':
                cells = cells[1:]
            if cells and cells[-1] == '':
                cells = cells[:-1]
            while len(cells) < ncols:
                cells.append('')
            cells = cells[:ncols]
            out.append(' & '.join([process_inline(escape_text(c)) for c in cells]) + r' \\')
            out.append(r'\hline')
        out.append(r'\end{longtable}')
        out.append(r'}')
        out.append('')
        table_rows = []
        in_table = False

    def flush_code():
        nonlocal code_lines, in_code
        if not code_lines:
            in_code = False
            return
        out.append('')
        out.append(r'\begin{verbatim}')
        for cl in code_lines:
            out.append(cl)
        out.append(r'\end{verbatim}')
        out.append('')
        code_lines = []
        in_code = False

    def flush_blockquote():
        nonlocal bq_lines, in_blockquote
        if not bq_lines:
            in_blockquote = False
            return
        out.append('')
        out.append(r'\begin{quote}')
        out.append(r'\itshape')
        for bl in bq_lines:
            out.append(bl)
        out.append(r'\end{quote}')
        out.append('')
        bq_lines = []
        in_blockquote = False

    def close_lists():
        nonlocal in_itemize, in_enumerate
        if in_itemize:
            out.append(r'\end{itemize}')
            in_itemize = False
        if in_enumerate:
            out.append(r'\end{enumerate}')
            in_enumerate = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # --- Code blocks ---
        if stripped.startswith('```'):
            if in_code:
                flush_code()
            else:
                close_lists()
                if in_table:
                    flush_table()
                if in_blockquote:
                    flush_blockquote()
                in_code = True
            i += 1
            continue

        if in_code:
            code_lines.append(line)
            i += 1
            continue

        # --- Tables ---
        if '|' in stripped and stripped.startswith('|') and stripped.endswith('|'):
            close_lists()
            if in_blockquote:
                flush_blockquote()
            if not in_table:
                in_table = True
            table_rows.append(stripped)
            i += 1
            continue
        elif in_table:
            flush_table()

        # --- Blockquotes ---
        if stripped.startswith('>'):
            close_lists()
            content = stripped[1:].strip()
            if not in_blockquote:
                in_blockquote = True
            if content:
                bq_lines.append(process_inline(escape_text(content)) + r' \\')
            else:
                bq_lines.append('')
            i += 1
            continue
        elif in_blockquote:
            flush_blockquote()

        # --- Horizontal rules ---
        if stripped in ('---', '***', '___'):
            close_lists()
            out.append('')
            out.append(r'\bigskip\noindent\rule{\textwidth}{0.4pt}\bigskip')
            out.append('')
            i += 1
            continue

        # --- Headings ---
        m = re.match(r'^(#{1,4})\s+(.*)', stripped)
        if m:
            close_lists()
            level = len(m.group(1))
            title = process_inline(escape_text(m.group(2)))
            cmds = {1: 'section', 2: 'subsection', 3: 'subsubsection', 4: 'paragraph'}
            out.append('')
            out.append('\\' + cmds[level] + '{' + title + '}')
            out.append('')
            i += 1
            continue

        # --- Display math ---
        if stripped.startswith('$$'):
            close_lists()
            # Check single-line $$...$$
            m2 = re.match(r'^\$\$(.*)\$\$$', stripped)
            if m2:
                out.append(r'\[' + m2.group(1) + r'\]')
                i += 1
                continue
            # Multi-line
            math_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('$$'):
                math_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            out.append(r'\[')
            out.append('\n'.join(math_lines))
            out.append(r'\]')
            continue

        # --- Numbered list ---
        m_num = re.match(r'^(\d+)\.\s+(.*)', stripped)
        if m_num:
            if in_itemize:
                out.append(r'\end{itemize}')
                in_itemize = False
            if not in_enumerate:
                out.append(r'\begin{enumerate}')
                in_enumerate = True
            out.append(r'\item ' + process_inline(escape_text(m_num.group(2))))
            i += 1
            continue

        # --- Bullet list ---
        m_bull = re.match(r'^[-*]\s+(.*)', stripped)
        if m_bull:
            if in_enumerate:
                out.append(r'\end{enumerate}')
                in_enumerate = False
            if not in_itemize:
                out.append(r'\begin{itemize}')
                in_itemize = True
            out.append(r'\item ' + process_inline(escape_text(m_bull.group(1))))
            i += 1
            continue

        # Close lists if we hit non-list content
        if stripped and (in_itemize or in_enumerate):
            # Check if this is a continuation line (indented)
            if not line.startswith('  '):
                close_lists()

        # --- Empty line ---
        if not stripped:
            i += 1
            # Don't add too many blank lines
            if out and out[-1] != '':
                out.append('')
            continue

        # --- Regular paragraph ---
        out.append(process_inline(escape_text(stripped)))
        i += 1

    # Flush remaining state
    close_lists()
    if in_table:
        flush_table()
    if in_code:
        flush_code()
    if in_blockquote:
        flush_blockquote()

    return '\n'.join(out)


def main():
    with open('/home/user/SergioSola/notebooks/00_research_programme_overview.ipynb') as f:
        nb = json.load(f)

    md_parts = []
    for c in nb['cells']:
        if c['cell_type'] == 'markdown':
            md_parts.append(''.join(c['source']))

    full_md = '\n\n'.join(md_parts)

    # Replace Unicode box-drawing characters with ASCII equivalents
    box_replacements = {
        '─': '-', '│': '|', '┌': '+', '┐': '+', '└': '+', '┘': '+',
        '├': '+', '┤': '+', '┬': '+', '┴': '+', '┼': '+',
        '▼': 'v', '▲': '^', '►': '>', '◄': '<', '◆': '*',
        '◀': '<', '▶': '>',
        '\u2500': '-', '\u2502': '|', '\u250c': '+', '\u2510': '+',
        '\u2514': '+', '\u2518': '+', '\u251c': '+', '\u2524': '+',
        '\u252c': '+', '\u2534': '+', '\u253c': '+',
        '\u25bc': 'v', '\u25b2': '^',
        '—': '---',  # em dash
        '–': '--',   # en dash
        ''': "'", ''': "'", '"': '``', '"': "''",
        '…': '...',
    }
    for old, new in box_replacements.items():
        full_md = full_md.replace(old, new)

    # Replace Unicode Greek/math chars ONLY in code blocks (```...```)
    # These are the chars that appear in ASCII diagrams inside code fences
    code_replacements = {
        'α': 'alpha', 'β': 'beta', 'γ': 'gamma', 'δ': 'delta',
        'ε': 'epsilon', 'λ': 'lambda', 'σ': 'sigma', 'τ': 'tau',
        'π': 'pi', 'θ': 'theta', 'φ': 'phi', 'ρ': 'rho',
        'μ': 'mu', 'ν': 'nu', 'ω': 'omega',
        'Σ': 'Sigma', 'Δ': 'Delta',
        '₁': '_1', '₂': '_2', '₃': '_3',
        '×': 'x',
    }
    def replace_in_code(m):
        block = m.group(0)
        for old, new in code_replacements.items():
            block = block.replace(old, new)
        return block
    full_md = re.sub(r'```.*?```', replace_in_code, full_md, flags=re.DOTALL)

    body = md_to_latex(full_md)

    preamble = r"""\documentclass[11pt,a4paper]{article}

% Encoding and fonts
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}

% Page geometry
\usepackage[margin=2.5cm]{geometry}

% Math
\usepackage{amsmath,amssymb,amsfonts}

% Tables
\usepackage{longtable}
\usepackage{booktabs}
\usepackage{array}

% Graphics and colors
\usepackage{graphicx}
\usepackage[dvipsnames]{xcolor}

% Hyperlinks
\usepackage[colorlinks=true,linkcolor=NavyBlue,urlcolor=NavyBlue,citecolor=NavyBlue]{hyperref}

% Code / verbatim
\usepackage{fancyvrb}
\usepackage{listings}
\lstset{
  basicstyle=\ttfamily\small,
  breaklines=true,
  frame=single,
  backgroundcolor=\color{gray!5},
  xleftmargin=1em,
  framexleftmargin=0.5em
}

% Spacing
\usepackage{setspace}
\onehalfspacing
\usepackage{parskip}

% Headers
\usepackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small\nouppercase{\leftmark}}
\fancyhead[R]{\small\thepage}
\renewcommand{\headrulewidth}{0.4pt}

% Title
\title{\LARGE\textbf{Research Programme Overview}\\[0.5em]
       \Large Non-Bank Financial Intermediation and Systemic Risk}
\author{Sergio Sola}
\date{February 2026}

\begin{document}
\maketitle
\thispagestyle{empty}

\begin{abstract}
\noindent This document provides a detailed research cookbook for a four-project
programme studying how non-bank financial intermediation (NBFI) creates, amplifies,
and transmits systemic risk. For each project, every analytical module specifies:
(1)~variables---exact names, definitions, sources, frequency, and level of aggregation;
(2)~model specification---full equation with every term defined;
(3)~estimation---method, software, key parameters;
(4)~output---what you get and how to interpret it; and
(5)~module linkages---how each module's output feeds into the next.
The unifying theme is that NBFI risks are fundamentally nonlinear: largely invisible
in normal times but activating powerfully during stress.
\end{abstract}

\tableofcontents
\newpage

"""

    postamble = r"""

\end{document}
"""

    tex = preamble + body + postamble
    outpath = '/home/user/SergioSola/reports/research_programme_overview.tex'
    with open(outpath, 'w') as f:
        f.write(tex)
    print(f'Wrote LaTeX to {outpath} ({len(tex)} chars)')


if __name__ == '__main__':
    main()
