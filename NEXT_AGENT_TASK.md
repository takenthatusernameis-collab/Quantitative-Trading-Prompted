# NEXT AGENT TASK — Cycle 884

## Context (read before acting)

Cycle 883 (commit `5d8ede9`) brought shortlist rank 7 (commodity/rate futures basis and roll yield) to the data-readiness gate and recorded an honest block:

* **Front-month series cached:** `data/raw/{CL-F,NG-F,GC-F,ZB-F}.parquet` (Yahoo Finance continuous front-month, `auto_adjust=False`), 2015-01-02 .. 2026-10-15, 2,964–2,965 sessions each, 0 missing closes, 0 duplicate dates, aligned-frame SHA-256 `f898cd42f5e42a29b50363258863f563daadb220c0896ecbef133b9b26446f9c`. Documented in `research/reports/futures_basis_data_integrity_001.md`.
* **Point-in-time roll NOT constructible:** no individual contract leg prices are available through the repository's supported fetcher (all probed legs CLZ24..CLZ25 returned 404 / delisted), so roll dates, roll prices and the roll cost actually paid are unobservable. A spliced continuous series was explicitly NOT back-tested.
* **Decision:** `futuresbasis_001` is **Blocked by data/infrastructure** (recorded in `research/experiments/futuresbasis_001.md` and `research/hypotheses/futuresbasis_001.md`, shortlist rank 7 cost column updated additively, no re-rank, scores unchanged 21/35).

Per `AGENTS.md` priority order, data readiness and integrity comes first, and the cycle ends with a "blocked by data" record — the next task resolves the block. It does **not** quietly back-test a spliced series.

## Objective

Resolve the roll block for shortlist rank 7 **OR** confirm it remains blocked with evidence:

1. **Find a point-in-time roll source.** Identify a free, accessible source of individual futures contract legs (front month + at least the next contract) with observable daily closes and enough volume/open-interest to detect the front-month roll point-in-time, plus a documented roll rule (roll date and roll price convention). No new paid data, services, or dependencies unless the evidence requires it and the benefit is documented.
2. **Construct the point-in-time front-month series** with an explicit, documented roll rule, detect the roll dates, and quantify the roll cost actually paid at observable closes.
3. **Extend `research/cost_admissibility_screen.py` (not a parallel tool)** to measure the roll-yield baseline for rank 7, including gate headroom and benchmark-parity cost, without moving any of the six existing candidates' published numbers.
4. **Reach a falsification decision:** if the roll-adjusted baseline cannot cover the roll cost plus the repository's 3 bp/unit model on its own window, the candidate is **Rejected/Failed on cost**; otherwise label it per the evidence.

If no viable roll source is found, record "Blocked by data/infrastructure" again with the evidence (what was tried, what failed, what would unblock it) and state the next step.

## Acceptance criteria

1. Either (a) a committed point-in-time front-month futures series with documented roll rule, detected roll dates, roll cost actually paid, and aligned-frame content hash; **or** (b) a committed "still blocked" record with the evidence.
2. If (a): `research/cost_admissibility_screen.py` exits 0 with `OVERALL: PASS`, the six existing candidates' published numbers unchanged to published precision, and rank 7 costed with the same conventions (turnover, drag at 3/5/10 bp, break-even, benchmark-parity, gate headroom, same-fold benchmark) plus a decision label written into `research/experiments/` and the shortlist cost column additively.
3. If (b): `research/experiments/futuresbasis_001.md` updated with the renewed block decision and evidence; shortlist rank 7 unchanged ("Blocked by data", no re-rank).
4. The shortlist is not silently re-ranked; any score/ordering change stated with its reason.
5. Hypothesis doc `research/hypotheses/futuresbasis_001.md` already exists; update only if the mechanism or cost model changes.

## Validation commands (run and report actual output)

```bash
python research/cost_admissibility_screen.py                 # OVERALL: PASS, exit 0
python -m pytest tests/test_cost_admissibility_screen.py -q   # all pass
python -m pytest -q                                           # all pass
python research/go_no_go_evaluation.py                        # NO-GO, side_effect_free: True
git status --porcelain data/ config/                          # empty
```

## Scope boundaries

* Research and backtesting only. No live trading, no credentials, no account access.
* Extend, do not duplicate: cost measurement lives in `research/cost_admissibility_screen.py`.
* No new dependencies, services, paid data, scheduled jobs, workflows or agents unless the task's evidence requires it and the benefit is documented.
* No re-optimization of the incumbent or of the six candidates the screen already covers; no change to any published number of theirs.
* Do not quietly back-test a spliced front-month series; a point-in-time roll that pays observable roll cost is required, else record the block.
* Do not dispatch this workflow and do not start additional agent sessions.
