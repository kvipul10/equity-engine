# Session 4 plan: Validation

Sessions 1-3 are merged (`main` @ cc5b8ea). This session checks the engine's diagnosis against published
analyst and press views, fixes what is wrong for general reasons, and finalises the README.

## 0. Ground rules (to keep the validation honest)

- **Pre-registration.** `validation/expected.md` and its machine-readable twin `validation/expected.yaml` are written
  and **committed before** analyse-all is run or any engine output is compared. The commit timestamp proves the order.
  Each expected item names, in advance, the engine signals that would count as "flagged". Signals are metric ids and
  flag ids chosen from the registry by meaning (`docs/metrics.md`, `docs/flags.md`), not from current outputs.
- **Disclosure.** Earlier sessions already produced reports, and I have seen parts of a few of them (TCS, HDFC Bank,
  DLF, Tata Steel, Yes Bank). expected.md will say so. Every expected item must cite a source found in this session.
- **Sources only.** Expected items come from cited analyst or press commentary: brokerage notes, results coverage,
  rating rationales, or the company's own disclosures where analysts quote them. Each item gets one or two source
  URLs and dates. Items must be financial and observable in reported numbers or KPIs. A widely cited qualitative item
  (e.g. US FDA compliance) is kept but tagged `qualitative`.
- **No per-company hacks.** Every fix must be general: a parsing rule, a metric definition, a sourced or `indicative`
  threshold, sector logic, or data. Each fix comes with a hand-computed test. Thresholds that change keep their
  source, or are marked `indicative` with a rationale.
- **Holdout.** The 4 peer companies (ICICI Bank, Infosys, Nestlé, HAL) get expected items too, written in the same
  pre-registered commit. They are **not looked at during fixing** and are scored once, before and after, to show
  whether the fixes generalise or overfit.

## 1. validation/expected.md (+ expected.yaml), written before running

- **Scope:**
  - the 16 `test` companies as of FY26
  - the 4 `peer` companies as the holdout set
  - Yes Bank as of FY18
- **Per company:** 3 main financial strengths and 3 main weaknesses, each with:
  - the claim in one line, the source URL(s) and date
  - `signals`, the engine metrics or flags that would show it (e.g. weakness "working capital stretch" → `dso`, `cash_conversion_cycle`, flag `C01`)
  - a tag: `financial`, `kpi` (needs a manual KPI) or `qualitative`
- **Yes Bank FY18:** the warning signs visible in reported financials before the collapse, with sources from that time or later retrospectives that point to the FY14-FY18 numbers (loan growth vs capital, CET1, RBI divergence disclosures, corporate concentration, bulk deposits). Each has signals as above.
- **Budget:** about 2 web searches per company (about 45 in total). I'll prefer results coverage and brokerage notes that quote numbers.

## 2. Comparison: `python -m engine validate`

New module `engine/validation.py` and a CLI command. Deterministic: it reads `expected.yaml` and the
`reports/*/analysis.json` and writes `validation/results.md` and `results.json`.

- **Match ("flagged"), per expected item:**
  - A strength is matched if at least one signal metric is GREEN at the as-of year.
  - A weakness is matched if at least one signal metric is RED, or AMBER with a deteriorating trend, or a signal flag fired.
- **Headline match:** the stricter level. The signal also appears in the report's top-6 strengths, weaknesses or watch, or in its bull/bear evidence. Reported alongside.
- **Miss:** an expected item that is not matched. The reason is then one of: no signal computable because data is missing, or the signal is computed but scored the other way.
- **False alarm:**
  1. **Automatic:** the engine says the opposite of an expected item, i.e. a signal for an expected strength is RED, or one for an expected weakness is GREEN and listed as a strength.
  2. **Reviewed:** every engine headline item (top-6 lists and high/medium flags) is checked against the sources. If it is wrong, the reason goes in `validation/adjudication.yaml` with a cited reason, so the count is reproducible.
- **Hit rate** = matched / expected items, overall and per archetype. It is reported:
  - with and without `qualitative` items
  - with and without items blocked by missing data
  - as headline hit rate
  - as false-alarm rate (false alarms / headline items)

## 3. Diagnose and fix loop

- For every miss and false alarm, record the cause: **parsing**, **metric definition**, **threshold**, **missing sector logic**, **missing data** (including manual KPIs I can source), or **qualitative**.
- Fix the general cause, add a test, rerun analyse-all and validate, and log the iteration (hit rate before and after, what changed).
- Stop when the overall hit rate stops improving, or when every remaining miss is explained by missing data or qualitative factors.
- Then score the holdout once.

## 4. validation/report.md

Contents:
- method, and the pre-registration commit
- final results tables (per company and per archetype)
- the iteration log
- every remaining miss and false alarm with its cause
- holdout result (before and after)
- archetypes ranked from most to least reliable, with the reason
- remaining limitations (data, single-company archetypes, unverified KPIs, qualitative factors)

## 5. README (finalised)

- **Mac setup:** python3 version check, `python3 -m venv .venv`, `source .venv/bin/activate`, `pip install -r requirements.txt`, `python -m pytest -q`.
- **Adding a new company:**
  1. Screener → Export to Excel
  2. rename to `<TICKER>.xlsx` in `data/raw/screener/`
  3. add a row to `data/universe.csv` (archetype, role, as-of)
  4. optionally copy `data/manual/templates/<archetype>_kpis.csv` to `data/manual/<TICKER>_kpis.csv` and fill it with sources
  5. run `analyse`
- **Commands:** analyse, analyse-all, compare, validate, kpi-templates, kpi-coverage, metrics, rules, build-benchmarks, ingest.
- **How to read the report:** a walk through the 8 sections and the colours, scores, confidence and driver chains, plus what the report does not do (no strategy or management judgement).

## 6. Order of work

1. Write expected.md/yaml for all 21 companies by web search, then commit and push (pre-registration).
2. Build the validate command and its tests.
3. Run analyse-all and validate (baseline).
4. Diagnose and fix loop.
5. Score the holdout.
6. Write report.md and the README.
7. Run the tests, commit, push, open a PR titled "Session 4: Validation", summarise in 10 lines or fewer.

## Decisions needed (defaults in bold)

1. Match rule: **a signal metric's RAG or flag status anywhere in the report counts as flagged**; the headline (top-6) match is reported as a secondary, stricter figure.
2. Holdout: **expected items for the 4 peers, scored only before and after fixing**. The alternative is no holdout, test companies only.
3. Qualitative items: **kept in expected.md, tagged, and reported with and without**. The alternative is to exclude them at the start.
