"""Driver trees (config/drivers.yaml) and exact change decomposition.

Link types (parent = f(children)):
  product      parent = prod(child^p): log decomposition, dln(parent) = sum p_i dln(child_i).
               Converted to parent units with the logarithmic mean L(a,b) = (a-b)/(ln a - ln b), which makes the
               split exact (Sato-Vartia). If any value is <= 0, an exact Shapley decomposition is used instead.
  sum          parent = const + sum(sign_i child_i): shift-share, each child contributes sign_i x its change.
  inverse_sum  parent = 1 / sum(sign_i child_i) (turnover = 1 / capital intensity): dln(parent) = -dln(CI) and the
               CI change is shared additively across its components.
  weighted_sum parent = sum(w_i r_i): mix effect (dw x mean r) + rate effect (mean w x dr), exact.
Each child gets a factor k = d(parent units) per unit change of the child; the contribution of a leaf to the root
is the product of factors along its path times the leaf's own change. Leaf contributions sum exactly to the
root's change (up to floating point).
"""
from __future__ import annotations

import itertools
import math
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .standardise import fy_year, year_label


class DriverError(ValueError):
    pass


def logmean(a: float, b: float) -> float:
    if a <= 0 or b <= 0:
        raise DriverError("log-mean needs positive values")
    if abs(a - b) <= 1e-12 * max(abs(a), abs(b)):
        return a
    return (a - b) / (math.log(a) - math.log(b))


def _parse_child(ch) -> Tuple[str, float, float]:
    """'-materials_pct' -> ('materials_pct', -1, 1); {'id': x, 'power': -1} -> (x, 1, -1)."""
    if isinstance(ch, dict):
        return ch["id"], float(ch.get("sign", 1.0)), float(ch.get("power", 1.0))
    s = str(ch).strip()
    if s.startswith("-"):
        return s[1:], -1.0, 1.0
    return s, 1.0, 1.0


def shapley_product(c0: List[float], c1: List[float], powers: List[float]) -> List[float]:
    n = len(c0)

    def f(sel):  # sel[i] True -> use t1 value
        v = 1.0
        for i in range(n):
            x = c1[i] if sel[i] else c0[i]
            if powers[i] < 0 and x == 0:
                return float("nan")
            v *= x ** powers[i]
        return v

    phi = [0.0] * n
    for i in range(n):
        others = [j for j in range(n) if j != i]
        for r in range(len(others) + 1):
            for S in itertools.combinations(others, r):
                w = math.factorial(r) * math.factorial(n - r - 1) / math.factorial(n)
                sel = [j in S for j in range(n)]
                with_i = list(sel)
                with_i[i] = True
                phi[i] += w * (f(with_i) - f(sel))
    return phi


class Tree:
    def __init__(self, spec: Dict):
        self.id = spec["id"]
        self.root = spec["root"]
        self.applies = spec.get("applies", ["ALL"])
        self.title = spec.get("title", self.id)
        self.links = spec["links"]

    def nodes(self) -> List[str]:
        seen, order = set(), []

        def visit(n):
            if n in seen:
                return
            seen.add(n)
            order.append(n)
            link = self.links.get(n) or {}
            kids = link.get("children") or [x for pair in link.get("pairs", []) for x in pair]
            for ch in kids:
                visit(_parse_child(ch)[0])

        visit(self.root)
        return order


def _value(get, node: str, lab: str) -> float:
    s = get(node)
    v = s.get(lab, np.nan) if s is not None else np.nan
    return float(v) if not pd.isna(v) else float("nan")


def decompose(tree: Tree, get, t0: str, t1: str, tol: float = 1e-6) -> Dict:
    """get(node_id) -> pd.Series by FY label. Returns contributions of every node to the root (root units)."""
    vals = {}
    for n in tree.nodes():
        vals[n] = (_value(get, n, t0), _value(get, n, t1))
    missing = [n for n, (a, b) in vals.items() if math.isnan(a) or math.isnan(b)]
    if missing:
        return {"status": "n/a", "reason": f"missing values for {', '.join(missing[:6])} at {t0} or {t1}"}

    contrib: Dict[str, float] = {tree.root: vals[tree.root][1] - vals[tree.root][0]}
    factor: Dict[str, float] = {tree.root: 1.0}
    methods: Dict[str, str] = {}
    inexact: List[str] = []
    leaves: List[str] = []
    paths: Dict[str, List[str]] = {tree.root: [tree.root]}

    def visit(node: str):
        link = tree.links.get(node)
        if not link:
            leaves.append(node)
            return
        p0, p1 = vals[node]
        kids = [_parse_child(ch) for ch in link.get("children", [])]
        typ = link["type"]
        k = {}
        if typ == "product":
            c0 = [vals[c][0] for c, _, _ in kids]
            c1 = [vals[c][1] for c, _, _ in kids]
            pw = [p for _, _, p in kids]
            rec0 = math.prod(x ** p for x, p in zip(c0, pw))
            rec1 = math.prod(x ** p for x, p in zip(c1, pw))
            if abs(rec0 - p0) > tol * max(1, abs(p0)) or abs(rec1 - p1) > tol * max(1, abs(p1)):
                inexact.append(node)
            if all(x > 0 for x in c0 + c1) and p0 > 0 and p1 > 0:
                Lp = logmean(p1, p0)
                for (c, _, pw_i), a, b in zip(kids, c0, c1):
                    k[c] = Lp * pw_i / logmean(b, a)
                methods[node] = "log"
            else:
                phi = shapley_product(c0, c1, pw)
                for (c, _, _), ph, a, b in zip(kids, phi, c0, c1):
                    k[c] = ph / (b - a) if b != a else 0.0
                methods[node] = "shapley"
        elif typ == "sum":
            const = float(link.get("const", 0.0))
            r0 = const + sum(s * vals[c][0] for c, s, _ in kids)
            r1 = const + sum(s * vals[c][1] for c, s, _ in kids)
            if abs(r0 - p0) > tol * max(1, abs(p0)) or abs(r1 - p1) > tol * max(1, abs(p1)):
                inexact.append(node)
            for c, s, _ in kids:
                k[c] = s
            methods[node] = "shift-share"
        elif typ == "inverse_sum":
            ci0 = sum(s * vals[c][0] for c, s, _ in kids)
            ci1 = sum(s * vals[c][1] for c, s, _ in kids)
            if ci0 <= 0 or ci1 <= 0:
                raise DriverError(f"{node}: capital intensity not positive")
            if abs(1 / ci0 - p0) > tol * max(1, abs(p0)) or abs(1 / ci1 - p1) > tol * max(1, abs(p1)):
                inexact.append(node)
            Lp, Lci = logmean(p1, p0), logmean(ci1, ci0)
            for c, s, _ in kids:
                k[c] = -s * Lp / Lci
            methods[node] = "inverse-sum (log)"
        elif typ == "weighted_sum":
            pairs = link["pairs"]  # [[weight_id, rate_id], ...]
            r0 = sum(vals[w][0] * vals[r][0] for w, r in pairs)
            r1 = sum(vals[w][1] * vals[r][1] for w, r in pairs)
            if abs(r0 - p0) > tol * max(1, abs(p0)) or abs(r1 - p1) > tol * max(1, abs(p1)):
                inexact.append(node)
            kids = []
            for w, r in pairs:
                k[w] = (vals[r][0] + vals[r][1]) / 2  # mix effect per unit weight change
                k[r] = (vals[w][0] + vals[w][1]) / 2  # rate effect per unit rate change
                kids += [(w, 1.0, 1.0), (r, 1.0, 1.0)]
            methods[node] = "mix/rate"
        else:
            raise DriverError(f"unknown link type {typ}")
        for c, _, _ in kids:
            factor[c] = factor[node] * k[c]
            contrib[c] = factor[c] * (vals[c][1] - vals[c][0])
            paths[c] = paths[node] + [c]
            visit(c)

    try:
        visit(tree.root)
    except DriverError as e:
        return {"status": "n/a", "reason": str(e)}
    d_root = contrib[tree.root]
    leaf_sum = sum(contrib[l] for l in leaves)
    nodes = {}
    for n in tree.nodes():
        nodes[n] = {"t0": vals[n][0], "t1": vals[n][1], "change": vals[n][1] - vals[n][0], "contribution": contrib.get(n),
                    "share_of_root": (contrib[n] / d_root) if abs(d_root) > 1e-12 else None,
                    "method": methods.get(n), "path": " > ".join(paths.get(n, [n]))}
    return {"status": "ok", "t0": t0, "t1": t1, "root_change": d_root, "leaf_sum": leaf_sum,
            "residual": d_root - leaf_sum, "inexact_nodes": inexact, "nodes": nodes, "leaves": leaves}


def top_leaves(result: Dict, n: int = 5) -> List[Dict]:
    if result.get("status") != "ok":
        return []
    rows = []
    for l in result["leaves"]:
        nd = result["nodes"][l]
        rows.append({"driver": l, "contribution": nd["contribution"], "share_of_root": nd["share_of_root"], "t0": nd["t0"],
                     "t1": nd["t1"], "change": nd["change"], "path": nd["path"]})
    rows.sort(key=lambda r: -abs(r["contribution"] or 0))
    return rows[:n]


def load_trees(cfg) -> List[Tree]:
    return [Tree(s) for s in (cfg.drivers.get("trees") or [])]


def run_trees(cfg, tokens, get, asof: str, available_labels) -> Dict:
    out = {}
    windows = cfg.scoring.get("drivers", {}).get("windows", [1, 3, 5])
    top_n = int(cfg.scoring.get("drivers", {}).get("top_n", 5))
    tol = float(cfg.scoring.get("drivers", {}).get("exactness_tolerance", 1e-6))
    y1 = fy_year(asof)
    for tree in load_trees(cfg):
        if not any(a in tokens for a in tree.applies):
            continue
        res_t = {"title": tree.title, "root": tree.root, "windows": {}}
        for w in windows:
            t0 = year_label(y1 - int(w))
            if t0 not in available_labels:
                res_t["windows"][f"{w}y"] = {"status": "n/a", "reason": f"{t0} not in data"}
                continue
            r = decompose(tree, get, t0, asof, tol)
            if r.get("status") == "ok":
                r["top_drivers"] = top_leaves(r, top_n)
            res_t["windows"][f"{w}y"] = r
        out[tree.id] = res_t
    return out
