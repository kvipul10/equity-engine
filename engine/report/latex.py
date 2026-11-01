"""Plain-text registry equations -> LaTeX for KaTeX (deterministic; None when an equation cannot be parsed).

The registry writes equations for people ("core PAT / average equity", "(Revenue_t / Revenue_t-3)^(1/3) - 1;
n/m if either value <= 0"). This converts the first clause to LaTeX with a small recursive-descent parser:

  rel  := add (('=' | '<' | '>' | '<=' | '>=') add)*
  add  := mul (('+' | '-') mul)*
  mul  := unary (('x' | '*' | '/') unary | unary)*      '/' -> \\dfrac, 'x' -> \\times, juxtaposition -> thin space
  unary:= '-' unary | power
  power:= atom ('^' atom)?
  atom := number | words | '(' rel ')' | '|' rel '|' | '[' rel ']' | func '(' rel (',' rel)* ')'

Words become \\text{...}; short suffixes after '_' become subscripts (Revenue_t-3 -> \\text{Revenue}_{t-3});
P/E-style names stay words; parentheticals that read as prose ('(reported)', '(current: TTM PAT when available)')
are kept as text. Clauses after ';' and definition clauses after ',' are rendered separately or left to the
plain-text equation, which the report always shows as the fallback.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import List, Optional, Tuple

FUNCS = {"sum3": r"\Sigma_{3}", "sum5": r"\Sigma_{5}", "sum10": r"\Sigma_{10}", "sum": r"\Sigma", "max": r"\max",
         "min": r"\min", "sd": r"\operatorname{sd}", "mean": r"\operatorname{mean}", "ln": r"\ln", "log": r"\log",
         "avg": r"\operatorname{avg}", "median": r"\operatorname{median}", "abs": r"\operatorname{abs}"}
PROSE = re.compile(r"(\bif\b|\bwhen\b|\bis\b|\bincl|\bexcl|reported|available|\be\.g\.|:|\bper\b|\bonly\b|\bRs\b|"
                   r"\bnot\b|\bor\b|\bfrom\b|\bwith\b|\bsee\b|\bvs\b|>|<|\bdefault\b)")
SUBSCRIPT = re.compile(r"^(t|T|t[+-]?\d+|\d+|[a-z]{1,2}|FY\d*|0)$")
RATIO_NAME = re.compile(r"^[A-Z]{1,6}/[A-Z]{1,9}$")
TOKEN = re.compile(r"""
    (?P<ws>\s+)
  | (?P<op><=|>=|[()\[\]|+\-/^=<>,*])
  | (?P<num>\d+(?:\.\d+)?%?)
  | (?P<word>[A-Za-z#&$%₹][\w.&#'$%]*(?:[-/][A-Za-z][\w.&#'%]*)*)
  | (?P<other>.)
""", re.X)


REL_OPS = {"=": "=", "<": "<", ">": ">", "<=": r"\le", ">=": r"\ge"}


class ParseError(Exception):
    pass


def _tokens(s: str) -> List[Tuple[str, str, int, int]]:
    out = []
    for m in TOKEN.finditer(s):
        kind = m.lastgroup
        if kind == "ws":
            continue
        val = m.group()
        if kind == "other":
            out.append(("punct", val, m.start(), m.end()))
            continue
        if kind == "word" and "/" in val and not RATIO_NAME.match(val):
            # COGS/Sales is a division; P/E, EV/IC are names
            parts = val.split("/")
            pos = m.start()
            for i, p in enumerate(parts):
                if i:
                    out.append(("op", "/", pos, pos + 1))
                    pos += 1
                out.append(("word", p, pos, pos + len(p)))
                pos += len(p)
            continue
        out.append((kind, val, m.start(), m.end()))
    # glue "_t" "-" "1" written without spaces (Revenue_t-1) into the word
    glued = []
    i = 0
    while i < len(out):
        k, v, a, b = out[i]
        if (k == "word" and re.search(r"_[tT]$", v) and i + 2 < len(out) and out[i + 1][1] in "-+"
                and out[i + 1][2] == b and out[i + 2][0] == "num" and out[i + 2][2] == out[i + 1][3]):
            glued.append(("word", v + out[i + 1][1] + out[i + 2][1], a, out[i + 2][3]))
            i += 3
            continue
        glued.append(out[i])
        i += 1
    return glued


def _esc(text: str) -> str:
    return (text.replace("\\", r"\backslash ").replace("{", r"\{").replace("}", r"\}").replace("#", r"\#")
            .replace("&", r"\&").replace("%", r"\%").replace("$", r"\$").replace("_", r"\_").replace("^", r"\^{}")
            .replace("~", r"\sim ").replace("₹", "Rs "))


def _word(w: str) -> str:
    if "_" in w:
        base, sub = w.rsplit("_", 1)
        if base and SUBSCRIPT.match(sub):
            return rf"\text{{{_esc(base)}}}_{{{_esc(sub)}}}"
    return rf"\text{{{_esc(w)}}}"


class _Parser:
    def __init__(self, src: str):
        self.src = src
        self.t = _tokens(src)
        self.i = 0

    def peek(self, off: int = 0):
        j = self.i + off
        return self.t[j] if j < len(self.t) else (None, None, len(self.src), len(self.src))

    def take(self):
        tok = self.peek()
        if tok[0] is None:
            raise ParseError("unexpected end")
        self.i += 1
        return tok

    def expect(self, v: str):
        tok = self.take()
        if tok[1] != v:
            raise ParseError(f"expected {v!r}, got {tok[1]!r}")

    def parse(self) -> str:
        out = self.rel(stop=())
        if self.peek()[0] is not None:
            raise ParseError(f"trailing {self.peek()[1]!r}")
        return out

    def rel(self, stop) -> str:
        left = self.add(stop)
        while self.peek()[1] in ("=", "<", ">", "<=", ">=") and self.peek()[1] not in stop:
            op = REL_OPS[self.take()[1]]
            left = f"{left} {op} {self.add(stop)}"
        return left

    def add(self, stop) -> str:
        left = self.mul(stop)
        while self.peek()[1] in ("+", "-") and self.peek()[1] not in stop:
            op = self.take()[1]
            left = f"{left} {op} {self.mul(stop)}"
        return left

    def _starts_atom(self, stop) -> bool:
        k, v, _, _ = self.peek()
        if k is None or v in stop:
            return False
        return k in ("num", "word") or v in ("(", "[") or (v == "|" and "|" not in stop)

    def mul(self, stop) -> str:
        left = self.unary(stop)
        while True:
            k, v, _, _ = self.peek()
            if v in stop:
                break
            if k == "word" and v == "x":
                self.take()
                left = rf"{left} \times {self.unary(stop)}"
            elif v == "*":
                self.take()
                left = rf"{left} \times {self.unary(stop)}"
            elif v == "/":
                self.take()
                left = rf"\dfrac{{{left}}}{{{self.unary(stop)}}}"
            elif self._starts_atom(stop):
                left = rf"{left}\,{self.unary(stop)}"
            else:
                break
        return left

    def unary(self, stop) -> str:
        if self.peek()[1] == "-":
            self.take()
            return f"-{self.unary(stop)}"
        return self.power(stop)

    def power(self, stop) -> str:
        base = self.atom(stop)
        if self.peek()[1] == "^":
            self.take()
            exp = self.atom(stop, in_exponent=True).replace(r"\dfrac", r"\tfrac")
            return f"{{{base}}}^{{{exp}}}"
        return base

    def _paren_prose(self) -> Optional[str]:
        """'(reported)' or '(current: TTM PAT when available)': prose, kept verbatim as text."""
        depth, j = 0, self.i
        while j < len(self.t):
            v = self.t[j][1]
            if v == "(":
                depth += 1
            elif v == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if j >= len(self.t):
            raise ParseError("unbalanced (")
        inner = self.src[self.t[self.i][3]:self.t[j][2]]
        only_words = all((t[0] == "word" and t[1] != "x") or t[1] == "," for t in self.t[self.i + 1:j])
        if PROSE.search(inner) or (only_words and j > self.i + 1):
            self.i = j + 1
            return rf"\;\text{{({_esc(inner.strip())})}}"
        return None

    def atom(self, stop, in_exponent: bool = False) -> str:
        k, v, _, _ = self.peek()
        if k is None:
            raise ParseError("missing operand")
        if k == "num":
            self.take()
            return _esc(v)
        if k == "word":
            if v in FUNCS and self.peek(1)[1] == "(":
                self.take()
                self.take()
                args = [self.rel(stop=(",", ")"))]
                while self.peek()[1] == ",":
                    self.take()
                    args.append(self.rel(stop=(",", ")")))
                self.expect(")")
                return rf"{FUNCS[v]}\left({', '.join(args)}\right)"
            words = [self.take()[1]]
            while self.peek()[0] == "word" and self.peek()[1] != "x" and self.peek()[1] not in FUNCS:
                words.append(self.take()[1])
            if len(words) == 1:
                return _word(words[0])
            last = _word(words[-1])
            if "_{" not in last:
                return rf"\text{{{_esc(' '.join(words))}}}"
            return rf"\text{{{_esc(' '.join(words[:-1]))}}}\," + last
        if v == "(":
            prose = self._paren_prose()
            if prose is not None:
                return prose
            self.take()
            inner = self.rel(stop=(")",))
            self.expect(")")
            return inner if in_exponent else rf"\left({inner}\right)"
        if v == "[":
            self.take()
            inner = self.rel(stop=("]",))
            self.expect("]")
            return rf"\left[{inner}\right]"
        if v == "|":
            self.take()
            inner = self.rel(stop=("|",))
            self.expect("|")
            return rf"\left\lvert {inner}\right\rvert"
        raise ParseError(f"unexpected {v!r}")


def _split_top(s: str, sep: str) -> List[str]:
    out, depth, cur = [], 0, ""
    i = 0
    while i < len(s):
        ch = s[i]
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if depth == 0 and s.startswith(sep, i):
            out.append(cur)
            cur = ""
            i += len(sep)
            continue
        cur += ch
        i += 1
    out.append(cur)
    return [x.strip() for x in out if x.strip()]


def _balanced(tex: str) -> bool:
    depth = 0
    for i, ch in enumerate(tex):
        if ch == "{" and (i == 0 or tex[i - 1] != "\\"):
            depth += 1
        elif ch == "}" and (i == 0 or tex[i - 1] != "\\"):
            depth -= 1
            if depth < 0:
                return False
    return depth == 0 and tex.count(r"\left") == tex.count(r"\right")


@lru_cache(maxsize=None)
def to_latex(equation: str) -> Optional[str]:
    """LaTeX for the first clause (plus ', X = ...' definitions), or None to fall back to the plain text."""
    if not equation or not equation.strip():
        return None
    first = _split_top(equation, "; ")[0]
    clauses = _split_top(first, ", ")
    keep = [clauses[0]] + [c for c in clauses[1:] if "=" in c and not PROSE.search(c.split("=", 1)[0])]
    try:
        parts = [_Parser(c).parse() for c in keep]
    except (ParseError, IndexError, ValueError):
        return None
    tex = r",\quad ".join(parts)
    return tex if _balanced(tex) else None
