"""As-of analysis uses only data up to that fiscal year (no look-ahead).

Proof by perturbation: build two identical projects, then in the second one replace EVERY value after the as-of
year (annual columns, all quarters, the export-date price and market cap, later manual KPIs) with random numbers,
for the company AND its same-archetype peers (enough peers that percentile scoring is active). The as-of reports
must be identical, and no later fiscal year may appear anywhere in them.
"""
from __future__ import annotations

import copy
import json
import random

import openpyxl
import pytest

from synthetic import CO, CO_YEARS, make_project, write_workbook

ASOF = "FY21"            # 5th of 10 synthetic years
LATER_COLS = range(7, 12)  # Data Sheet columns G..K = FY22..FY26 (B = FY17)
PEERS = {"PEERA": 1.10, "PEERB": 0.90, "PEERC": 1.25}


def _peer_rows():
    return "".join(f"{t},consumer_manufacturing,peer,FY26\n" for t in PEERS)


def _add_peers(root):
    for t, f in PEERS.items():
        spec = copy.deepcopy(CO)
        spec["employee"] = [round(v * f, 2) for v in spec["employee"]]
        spec["cfo"] = [round(v * (2 - f), 2) for v in spec["cfo"]]
        write_workbook(root / "data" / "raw" / "screener" / f"{t}.xlsx", spec, CO_YEARS, f"{t} LTD")


def _scramble(path, rng):
    wb = openpyxl.load_workbook(path)
    ws = wb["Data Sheet"]
    for r in list(range(17, 32)) + list(range(57, 73)) + list(range(82, 86)) + [90, 93]:
        for c in LATER_COLS:
            ws.cell(r, c, rng.uniform(-5000, 5000))
    for r in range(42, 51):          # every quarter is after FY21
        for c in range(2, 12):
            ws.cell(r, c, rng.uniform(-5000, 5000))
    ws.cell(8, 2, rng.uniform(1, 9999))    # current price
    ws.cell(9, 2, rng.uniform(1, 99999))   # market cap
    wb.save(path)


def _strip(rep):
    r = json.loads(json.dumps(rep))
    r["data_notes"] = [n for n in r["data_notes"] if n["category"] != "source"]  # file hash differs by design
    return r


@pytest.fixture(scope="module")
def pair(tmp_path_factory):
    a = make_project(tmp_path_factory.mktemp("asof_a"), extra_universe=_peer_rows())
    b = make_project(tmp_path_factory.mktemp("asof_b"), extra_universe=_peer_rows())
    _add_peers(a)
    _add_peers(b)
    rng = random.Random(42)
    for t in ["SYNTHCO", *PEERS]:
        _scramble(b / "data" / "raw" / "screener" / f"{t}.xlsx", rng)
    man = b / "data" / "manual" / "SYNTHCO_kpis.csv"
    lines = man.read_text().splitlines()
    out = [lines[0]] + [l if l.split(",")[0] in ("FY17", "FY18", "FY19", "FY20", "FY21") else
                        ",".join([l.split(",")[0], l.split(",")[1], str(rng.uniform(0, 99))] + l.split(",")[3:]) for l in lines[1:]]
    man.write_text("\n".join(out) + "\n")
    return a, b


def _analyse(root, ticker, asof):
    from engine.analysis import PeerSet, analyse
    from engine.config import Config
    from engine.paths import Paths

    cfg = Config.load(Paths.default(root))
    return analyse(ticker, cfg, asof=asof, peers=PeerSet(cfg))


def test_asof_output_identical_when_future_is_scrambled(pair):
    a, b = pair
    ra, rb = _analyse(a, "SYNTHCO", ASOF), _analyse(b, "SYNTHCO", ASOF)
    assert ra["asof"]["fy"] == ASOF and "as-of" in ra["asof"]["mode"]
    assert _strip(ra) == _strip(rb)


def test_percentile_peers_also_truncated(pair):
    a, _ = pair
    ra = _analyse(a, "SYNTHCO", ASOF)
    bases = {m.get("level", {}).get("basis") for m in ra["metrics"].values() if m.get("level")}
    assert "percentile" in bases, "peer percentile mode should be active (4 same-archetype companies)"


def _data_only(rep):
    """Drop config provenance (band rationales, benchmark sources/dates): those describe 2026 benchmarks, not company data.
    The benchmark-vintage limitation is documented in docs/methodology.md."""
    r = json.loads(json.dumps(rep))
    for m in r["metrics"].values():
        m.pop("band", None)
    r["cost_of_capital"].pop("sources", None)
    r["cost_of_capital"].pop("notes", None)
    r.pop("sector_references", None)
    return r


def test_no_later_year_appears_anywhere(pair):
    a, _ = pair
    txt = json.dumps(_data_only(_analyse(a, "SYNTHCO", ASOF)))
    for fy in ("FY22", "FY23", "FY24", "FY25", "FY26", "2021-06", "2026-09"):
        assert fy not in txt, f"{fy} leaked into an as-of {ASOF} report"


def test_scrambling_does_change_latest_run(pair):
    """Sanity check that the perturbation is real: the latest (non as-of) analyses differ."""
    a, b = pair
    assert _strip(_analyse(a, "SYNTHCO", None))["metrics"]["roe"] != _strip(_analyse(b, "SYNTHCO", None))["metrics"]["roe"]


def test_yesbank_asof_fy18_uses_only_data_up_to_fy18(real_cfg):
    """Screener data covers FY17-FY18 at this as-of; manual KPIs (annual reports) extend the window back to FY14."""
    from engine.analysis import analyse

    rep = analyse("YESBANK", real_cfg, asof="FY18")
    assert rep["asof"]["data_window"] == "FY17-FY18"
    assert rep["asof"]["manual_kpi_window"] == "FY14-FY18"
    assert rep["asof"]["price_basis"] == "fy_end_asof"
    assert rep["asof"]["latest_quarter_used"] is None
    allowed = {f"FY{y}" for y in range(14, 19)}
    for m in rep["metrics"].values():
        assert set(m["series"]) <= allowed
    txt = json.dumps(_data_only(rep))
    for fy in ("FY19", "FY20", "FY21", "FY22", "FY23", "FY24", "FY25", "FY26"):
        assert fy not in txt


def test_yesbank_blowup_flags_fire_asof_fy18(real_cfg):
    """Blow-up test: with only FY17-FY18 data the engine flags the capital/growth mismatch that preceded the 2019-20 collapse."""
    from engine.analysis import analyse

    rep = analyse("YESBANK", real_cfg, asof="FY18")
    ids = {f["id"] for f in rep["flags"]["triggered"]}
    assert {"A06", "B06"} <= ids
