#!/usr/bin/env python3
"""Fix formatting issues in the LaTeX file: wide verbatim blocks and tables."""

import re

with open('/home/user/SergioSola/reports/research_programme_overview.tex', 'r') as f:
    content = f.read()

# --- Fix 1: Add adjustbox package to preamble ---
content = content.replace(
    r'\usepackage{graphicx}',
    r'\usepackage{graphicx}' + '\n' + r'\usepackage{adjustbox}'
)

# --- Fix 2: Replace ALL verbatim blocks with adjustbox-wrapped versions ---
# This ensures they never overflow regardless of content width
pattern = re.compile(r'\\begin\{verbatim\}(.*?)\\end\{verbatim\}', re.DOTALL)

def fix_verbatim(m):
    inner = m.group(1)
    # Use adjustbox to shrink any verbatim to fit within text width
    return ('\\begin{adjustbox}{max width=\\textwidth}\n'
            '\\begin{minipage}{1.5\\textwidth}\n'
            '\\begin{verbatim}' + inner +
            '\\end{verbatim}\n'
            '\\end{minipage}\n'
            '\\end{adjustbox}')

content = pattern.sub(fix_verbatim, content)

# Remove the previous \scriptsize \begin{center}...\end{center} wrappers
# that were added in the previous fix
content = content.replace(
    '\\begin{center}\n\\scriptsize\n\\begin{adjustbox}',
    '\\begin{adjustbox}'
)
content = content.replace(
    '\\end{adjustbox}\n\\end{center}',
    '\\end{adjustbox}'
)

# --- Fix 3: Fix 6-column tables ---
# The 0.15 * 6 = 0.90 + padding overflows. Use proportional widths.
# Variable | Symbol | Definition | Source | Frequency | Level
content = content.replace(
    r'{|p{0.10\textwidth}|p{0.08\textwidth}|p{0.24\textwidth}|p{0.18\textwidth}|p{0.12\textwidth}|p{0.11\textwidth}|}',
    r'{|p{0.09\textwidth}|p{0.07\textwidth}|p{0.25\textwidth}|p{0.18\textwidth}|p{0.13\textwidth}|p{0.10\textwidth}|}'
)

# --- Fix 4: Fix 3-column {|l|l|l|} tables - use p{} columns instead ---
# These are the "Force | Normal | Stress" type tables and others
content = content.replace(
    r'\begin{longtable}{|l|l|l|}',
    r'\begin{longtable}{|p{0.22\textwidth}|p{0.33\textwidth}|p{0.33\textwidth}|}'
)

# --- Fix 5: Fix 4-column tables (Parameter | Symbol | Definition | Value) ---
content = content.replace(
    r'{|p{0.21\textwidth}|p{0.21\textwidth}|p{0.21\textwidth}|p{0.21\textwidth}|}',
    r'{|p{0.15\textwidth}|p{0.15\textwidth}|p{0.33\textwidth}|p{0.22\textwidth}|}'
)

# --- Fix 6: Very long \textbf{} lines that don't wrap ---
# The chain description on one line - add a line break
content = content.replace(
    r'\textbf{Equity shocks $\rightarrow$ FX movements $\rightarrow$ hedging cost changes $\rightarrow$ NBFI portfolio adjustment $\rightarrow$ cross-border bond flow reversal $\rightarrow$ feedback to asset prices}',
    r'''\begin{center}
\textbf{Equity shocks $\rightarrow$ FX movements $\rightarrow$ hedging cost changes $\rightarrow$ NBFI portfolio adjustment}\\
\textbf{$\rightarrow$ cross-border bond flow reversal $\rightarrow$ feedback to asset prices}
\end{center}'''
)

with open('/home/user/SergioSola/reports/research_programme_overview.tex', 'w') as f:
    f.write(content)

print(f'Fixed. Total length: {len(content)} chars')
