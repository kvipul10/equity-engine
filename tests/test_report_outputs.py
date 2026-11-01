"""report.html, analysis.xlsx and compare.html on synthetic companies: structure, self-containment, determinism,
no look-ahead, workbook contents and the CLI."""
from __future__ import annotations

import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import openpyxl
import pytest

from synthetic import make_project
from synthetic_sectors import add_sector_companies

REPO = Path(__file__).resolve().parent.parent
SECTIONS = ("summary", "findings", "tree", "flags", "drivers", "valuation", "missing", "bullbear", "notes")
VOID = {"meta", "link", "br", "img", "input", "hr", "col", "source", "area", "base", "wbr"}


@pytest.fixture(scope="module")
def sroot(tmp_path_factory):
    return add_sector_companies(make_project(tmp_path_factory.mktemp("report")))


@pytest.fixture(scope="module")
def scfg(sroot):
    from engine.config import Config
    from engine.paths import Paths

    return Config.load(Paths.default(sroot))


@pytest.fixture(scope="module")
def reps(scfg):
    from engine.analysis import PeerSet, analyse

    peers = PeerSet(scfg)
    return {t: analyse(t, scfg, peers=peers) for t in ("SYNTHCO", "SYNTHBK", "SYNTHBKNP", "SYNTHRE")}


class _Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.errors, self.ids, self.res = [], [], [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "script" and a.get("src"):
            self.res.append(a["src"])
        if tag == "link" and a.get("href"):
            self.res.append(a["href"])
        if tag == "img":
            self.res.append(a.get("src", ""))
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"unbalanced </{tag}> (open: {self.stack[-3:]})")
            if tag in self.stack:
                while self.stack and self.stack.pop() != tag:
                    pass
            return
        self.stack.pop()


def _parse(html: str) -> _Tags:
    p = _Tags()
    p.feed(html)
    p.close()
    return p


@pytest.mark.parametrize("t", ["SYNTHCO", "SYNTHBK", "SYNTHRE"])
def test_report_html_structure_and_self_contained(reps, scfg, t):
    from engine.report.html import KATEX_CSS, KATEX_JS, render_report

    rep = reps[t]
    html = render_report(rep, scfg)
    p = _parse(html)
    assert not p.errors and not p.stack, (p.errors[:3], p.stack)
    for s in SECTIONS:
        assert s in p.ids, s
    # the 8 pillar nodes carry the RAG from the JSON, and each opens a panel
    for pid, pv in rep["pillars"].items():
        rag = pv["rag"] if pv["rag"] in ("green", "amber", "red") else "na"
        assert re.search(rf'<button type="button" class="pnode {rag}" data-target="pillar-{pid}"', html), pid
        assert f'id="pillar-{pid}"' in html
    # self-contained: the only resources loaded are the pinned KaTeX files; no images, no CSS url()/@import
    assert set(p.res) == {KATEX_CSS, KATEX_JS}
    assert "url(" not in html.split("<style>")[1].split("</style>")[0] and "@import" not in html
    # every finding and bull/bear line is on the page (escaped the same way)
    from markupsafe import escape

    f = rep["findings"]
    for k in ("strengths", "weaknesses", "watch"):
        for c in f[k]:
            assert str(escape(c["text"])) in html
    for b in f["bull"] + f["bear"]:
        assert str(escape(b["text"])) in html


def test_report_html_is_deterministic(reps, scfg):
    from engine.report.html import render_report

    assert render_report(reps["SYNTHCO"], scfg) == render_report(reps["SYNTHCO"], scfg)


def test_bank_report_paths(reps, scfg):
    from engine.report.html import render_report

    bk = render_report(reps["SYNTHBK"], scfg)
    assert 'id="tree-bank_dupont"' in bk and "replaces generic" in bk
    assert "ROIC is not meaningful for bank-like companies" in bk and 'id="tree-roic_tree"' not in bk
    assert "EV-based multiples are not used" in bk
    np_ = reps["SYNTHBKNP"]
    miss = {k["kpi"]: k for k in np_["findings"]["missing_data"]["kpis"]}
    assert "provisions_cr" in miss and miss["provisions_cr"]["required"]
    assert "BK08" in miss["provisions_cr"]["flags"] and "bank_dupont" in miss["provisions_cr"]["trees"]
    assert {"credit_cost", "provisions_to_assets"} <= set(miss["provisions_cr"]["metrics"])
    html = render_report(np_, scfg)
    assert 'id="tree-fin_roe"' in html and "Sector tree &#39;bank_dupont&#39; not computable" in html


def test_real_estate_report_has_sector_tree(reps, scfg):
    from engine.report.html import render_report

    html = render_report(reps["SYNTHRE"], scfg)
    assert 'id="tree-real_estate_cash"' in html and 'id="tree-roe_dupont"' in html and 'id="tree-roic_tree"' in html


def test_findings_lines_carry_number_trend_and_chain(reps):
    f = reps["SYNTHCO"]["findings"]
    items = f["strengths"] + f["weaknesses"] + f["watch"]
    assert items and all(len(f[k]) <= 6 for k in ("strengths", "weaknesses", "watch"))
    for k in ("strengths", "weaknesses", "watch"):
        per = {}
        for c in f[k]:
            per[c["pillar"]] = per.get(c["pillar"], 0) + 1
            assert c["score"] == pytest.approx(c["severity"] * c["confidence"], abs=1e-5)
        assert max(per.values(), default=0) <= 2
        assert [c["score"] for c in f[k]] == sorted((c["score"] for c in f[k]), reverse=True)
    chained = [c for c in items if c.get("chain")]
    assert chained, "at least one finding should carry a driver chain"
    for c in chained:
        assert c["chain"] in c["text"] and c["number"] in c["text"]
    assert all(b["text"].endswith("]") for b in f["bull"] + f["bear"]), "every bull/bear bullet cites its evidence id"


# ---------------------------------------------------------------------------------------------- as-of
def _render_asof(root, asof="FY21"):
    from engine.analysis import PeerSet, analyse
    from engine.config import Config
    from engine.paths import Paths
    from engine.report.html import render_report

    cfg = Config.load(Paths.default(root))
    rep = analyse("SYNTHCO", cfg, asof=asof, peers=PeerSet(cfg))
    return rep, render_report(rep, cfg), cfg


def test_asof_report_has_no_look_ahead(tmp_path_factory):
    a, b = _make_pair(tmp_path_factory)
    ra, ha, cfg = _render_asof(a)
    rb, hb, _ = _render_asof(b)
    def norm(h):  # the source-file hash in the data notes is provenance (the scrambled file differs), not data
        return re.sub(r"sha256 [0-9a-f]+", "sha256 <hash>", h)
    assert norm(ha) == norm(hb), "scrambling the future changed the FY21 report"
    for fy in ("FY22", "FY23", "FY24", "FY25", "FY26"):
        assert fy not in ha, fy
    from engine.report.xlsx import write_xlsx

    pa, pb = tmp_path_factory.mktemp("xa"), tmp_path_factory.mktemp("xb")
    wa, wb = openpyxl.load_workbook(write_xlsx(ra, pa, cfg)), openpyxl.load_workbook(write_xlsx(rb, pb, cfg))
    assert wa.sheetnames == wb.sheetnames
    for name in wa.sheetnames:
        va = [[c for c in r] for r in wa[name].iter_rows(values_only=True)]
        vb = [[c for c in r] for r in wb[name].iter_rows(values_only=True)]
        assert va == vb, name
        assert not any(isinstance(c, str) and re.fullmatch(r"FY2[2-6]", c) for r in va for c in r), name


def _make_pair(tmp_path_factory):
    import test_asof as A

    a = make_project(tmp_path_factory.mktemp("ra"), extra_universe=A._peer_rows())
    b = make_project(tmp_path_factory.mktemp("rb"), extra_universe=A._peer_rows())
    A._add_peers(a)
    A._add_peers(b)
    import random

    rng = random.Random(42)
    for t in ["SYNTHCO", *A.PEERS]:
        A._scramble(b / "data" / "raw" / "screener" / f"{t}.xlsx", rng)
    man = b / "data" / "manual" / "SYNTHCO_kpis.csv"
    lines = man.read_text().splitlines()
    out = [lines[0]] + [l if l.split(",")[0] in ("FY17", "FY18", "FY19", "FY20", "FY21") else
                        ",".join([l.split(",")[0], l.split(",")[1], str(rng.uniform(0, 99))] + l.split(",")[3:]) for l in lines[1:]]
    man.write_text("\n".join(out) + "\n")
    return a, b


# ---------------------------------------------------------------------------------------------- xlsx
def test_xlsx_sheets_and_values(reps, scfg, tmp_path):
    from engine.registry import PILLAR_NAMES, PILLARS
    from engine.report.xlsx import write_xlsx

    rep = reps["SYNTHCO"]
    wb = openpyxl.load_workbook(write_xlsx(rep, tmp_path, scfg))
    assert wb.sheetnames == ["Summary", *[PILLAR_NAMES[p] for p in PILLARS], "Flags", "Drivers"]
    ws = wb["4 Returns"]
    head = [c.value for c in ws[1]]
    years = list(rep["metrics"]["roe"]["series"])
    row = next(r for r in ws.iter_rows(min_row=2, values_only=True) if r[0] == "roe")
    for y in years:
        v = row[head.index(y)]
        exp = rep["metrics"]["roe"]["series"][y]
        assert (v is None and exp is None) or v == pytest.approx(exp)
    assert row[head.index("Latest")] == pytest.approx(rep["metrics"]["roe"]["value"])
    assert row[head.index("RAG")] == rep["metrics"]["roe"]["rag"]
    flags = [r for r in wb["Flags"].iter_rows(min_row=2, values_only=True)]
    n = len(rep["flags"]["triggered"]) + len(rep["flags"]["not_evaluable"]) + len(rep["flags"]["clear"])
    assert len(flags) == n
    drv = [r for r in wb["Drivers"].iter_rows(min_row=2, values_only=True)]
    assert {r[0] for r in drv} == set(rep["drivers"])


# ---------------------------------------------------------------------------------------------- CLI
def _cli(root, *args):
    return subprocess.run([sys.executable, "-m", "engine", "--root", str(root), *args], cwd=REPO, capture_output=True, text=True)


def test_cli_writes_html_and_xlsx(sroot):
    p = _cli(sroot, "analyse", "SYNTHRE", "--quiet")
    assert p.returncode == 0, p.stderr
    out = sroot / "reports" / "SYNTHRE"
    assert (out / "report.html").stat().st_size > 10_000 and (out / "analysis.xlsx").exists()


def test_cli_compare(sroot):
    p = _cli(sroot, "compare", "SYNTHCO", "SYNTHBK", "SYNTHRE")
    assert p.returncode == 0, p.stderr
    html = (sroot / "reports" / "compare.html").read_text()
    t = _parse(html)
    assert not t.errors and not t.stack
    for tk in ("SYNTHCO", "SYNTHBK", "SYNTHRE"):
        assert tk in html
    assert "Archetypes differ" in html and html.count('<rect class="s') >= 16
    assert _cli(sroot, "compare", "SYNTHCO").returncode == 1
    assert _cli(sroot, "compare", *["SYNTHCO", "SYNTHBK", "SYNTHRE", "SYNTHIT", "SYNTHFM", "SYNTHAU"]).returncode == 1
