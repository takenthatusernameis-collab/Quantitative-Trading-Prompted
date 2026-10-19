# Opportunity Shortlist — Scored Candidates

**Generated:** 2026-10-12 07:52:57 UTC
**Code revision:** a5d5971
**Method:** Phase 1 of the AGENTS.md Market Opportunity Search. Each Candidate is scored 1-5 against the seven criteria ((a)-(g)) using only evidence available in this repository (cached data, config files, prior experiment records). Scores are pre-test structural assessments — NOT backtest results. No new backtests were run to produce this shortlist.

**Scoring legend:** 1 = poor/infeasible, 2 = weak, 3 = adequate, 4 = strong, 5 = excellent/feasible. Overall = sum of (a)-(g), max 35.

**Verdict categories:** Credible candidate (promotion gates passed) / Exploratory signal (valid test possible, untested) / Blocked by data (cannot form a valid test with available data) / Rejected (evidence shows no viable edge or infeasible execution).

## Candidate Scoring Summary

| Rank | Candidate | (a) Data Quality | (b) Structural Mech | (c) Net Return | (d) Robustness | (e) Liquidity | (f) Automation | (g) Diversification | Overall | Verdict |
|------|-----------|------------------|---------------------|----------------|----------------|---------------|----------------|---------------------|---------|---------|
| 1 | TSMOM incumbent | 5 | 4 | 4 | 4 | 5 | 5 | 5 | **32/35** | Credible candidate |
| 2 | Long-only cross-sectional momentum, broad 18-ETF universe | 5 | 5 | 3 | 3 | 5 | 4 | 4 | **29/35** | Exploratory signal |
| 3 | Sector rotation | 5 | 4 | 3 | 3 | 5 | 4 | 4 | **28/35** | Exploratory signal |
| 4 | Calendar / rebalancing effects | 5 | 3 | 2 | 3 | 5 | 4 | 4 | **26/35** | Exploratory signal |
| 5 | TSMOM parameter variants | 5 | 4 | 2 | 2 | 5 | 5 | 2 | **25/35** | Rejected |
| 6 | Macro regime overlay extension | 4 | 4 | 3 | 3 | 3 | 4 | 3 | **24/35** | Exploratory signal |
| 7 | Commodity/rate futures basis and roll yield | 2 | 4 | 3 | 2 | 3 | 2 | 5 | **21/35** | Blocked by data |
| 8 | Crypto perpetual funding-rate carry | 2 | 4 | 3 | 2 | 5 | 3 | 1 | **20/35** | Blocked by data |
| 9 | Volatility risk premium | 2 | 4 | 2 | 2 | 2 | 2 | 4 | **18/35** | Blocked by data |
| 10 | Intraday session / time-of-day effects | 1 | 3 | 2 | 1 | 4 | 2 | 4 | **17/35** | Rejected |

**Data availability driving the scores (computed from the live cache):**

| Data Class | Cached | Consequence |
|------------|--------|-------------|
| Daily ETF OHLCV (18 ETFs + ^VIX) | YES | TSMOM, cross-sectional, sector, calendar, and regime strategies are all testable offline |
| Crypto spot/perp + funding | NO | Funding-carry candidates blocked from offline testing |
| Futures (commodity/rate) | YES (front-month CL/NG/GC/ZB cached) | Basis/roll-yield candidates blocked by unobservable roll **prices**, not by missing prices or missing roll **dates** (`data/raw/{CL-F,NG-F,GC-F,ZB-F}.parquet` cached; roll dates observable from the cached volume signature, Cycle 884; the leg closes at a roll are not) |
| Forex spot | NO | Forex carry blocked (no rate differentials regardless) |
| Intraday history | NO | Session-effect candidates rejected |
| Tradeable vol instrument | NO (^VIX index only) | Vol-risk-premium candidates blocked |
| Options/funding/basis/borrow history | NO | Derivatives and short-side strategies blocked |

---

## Cost-Admissibility Column (Cycle 881 — additive; no existing row is re-ranked)

**Added 2026-10-19 by `research/cost_admissibility_screen.py` (read-only).**
The shortlist above scores (c) Net Return on a **structural** basis and states no candidate's
annualized cost drag. Cycle 880 then rejected the overnight-session candidate on cost: a gross
premium of +9.16%/yr against 15.12%/yr of drag, because an overnight-only leg must be flat
during the day and therefore round-trips twice per session (504 units of annual turnover).
This section adds the missing column for the candidates the screen covers. **No row of the
summary table above is removed, re-scored or re-ranked**; the ranking stays as it was, and the
cost evidence is published next to it.

| Shortlist rank | Candidate | Annual turnover (units/yr) | Drag @3 bp/unit | Gross signal | Min gross signal needed @3 bp | Break-even cost | Admissibility |
|---|---|---|---|---|---|---|---|
| 1 | TSMOM incumbent (`tsmomentum_spytrend_001`) | 12.16 | +0.3649%/yr | +13.8825%/yr | +0.3649%/yr | 106.75 bp/unit | **ADMISSIBLE** |
| 4 | Calendar / rebalancing effects (`calendar_effects_001`) | 24.13 | +0.7239%/yr | +2.7326%/yr | +0.7239%/yr | 11.16 bp/unit | **ADMISSIBLE** |
| 10 | Intraday session / time-of-day effects (overnight variant, `overnight_capture_001`) | 504.00 | +15.1200%/yr | +9.1558%/yr | +15.1200%/yr | 1.74 bp/unit | **INADMISSIBLE** |

Two things the cost column changes and one it does not:

* **It confirms the Rank-10 rejection on a second, independent axis.** The session-effect
  candidate fails the cost screen at the repository's own 3 bp/unit model: its break-even cost
  is 1.74 bp/unit, 58% of what the model charges, and it needs a cost of only 0.29 bp/unit to
  match simply holding the same basket close-to-close.
* **It does not promote the Rank-4 candidate.** `calendar_effects_001` clears the cost screen
  comfortably (break-even 11.16 bp/unit, 3.7x the model cost), but on the same folds it would
  have to be **paid 22.69 bp/unit** to merely match passive close-to-close holding of the same
  basket. Cost-admissibility is necessary and **not** sufficient: a candidate can survive its
  costs and still have no edge.
* **It leaves the shortlist's ranking intact.** Ranked by break-even cost the three screened
  candidates order as incumbent > calendar > session-effect, which is the same order as the
  gross-effect ranking above. The screen is a filter to apply **before** short-listing, not a
  re-ranking of the list.

**Coverage:** this cycle screens the three candidates whose daily gross-return and turnover
series can be rebuilt from the committed cache and the committed artifacts. Ranks 2, 3 and 6
(`csmomentum_001`, `sectorrotation_001`, `macroregime_001`) are **not** covered yet; their cost
evidence is still only the structural (c) score above. Full evidence:
`research/reports/cost_admissibility_screen_001.md`.

---

## Cost-Admissibility Column, completed (Cycle 882 — additive; no existing row is re-ranked)

**Added 2026-10-19 by `research/cost_admissibility_screen.py` (read-only).**
Cycle 881 left ranks 2, 3 and 6 without a cost basis. The screen was **extended** (not
duplicated) to cover them, using the repository's already-validated config-faithful month-end
construction, and one further decision number was added: the **gate headroom**, i.e. the cost per
unit at which the candidate's net walk-forward mean OOS Sharpe falls to the repository's own
0.9 promotion threshold. **No row of the summary table above is removed, re-scored or re-ranked**,
and no number of the Cycle 881 cost column changes.

### Costed candidates (six of the ten rows)

| Shortlist rank | Candidate | Annual turnover (units/yr) | Drag @3 bp/unit | Gross signal | Min gross signal needed @3 bp | Break-even cost | Admissibility | Gate headroom (WF Sharpe = 0.9) |
|---|---|---|---|---|---|---|---|---|
| 1 | TSMOM incumbent (`tsmomentum_spytrend_001`) | 12.16 | +0.3649%/yr | +13.8825%/yr | +0.3649%/yr | 106.75 bp/unit | **ADMISSIBLE** | +37.51 bp/unit |
| 2 | Long-only cross-sectional momentum, broad 18-ETF universe (`csmomentum_001`) | 2.23 | +0.0668%/yr | +9.4355%/yr | +0.0668%/yr | 402.32 bp/unit | **ADMISSIBLE** | -30.10 bp/unit (negative) |
| 3 | Sector rotation (`sectorrotation_001`) | 3.00 | +0.0899%/yr | +7.2161%/yr | +0.0899%/yr | 231.71 bp/unit | **ADMISSIBLE** | -25.31 bp/unit (negative) |
| 4 | Calendar / rebalancing effects (`calendar_effects_001`) | 24.13 | +0.7239%/yr | +2.7326%/yr | +0.7239%/yr | 11.16 bp/unit | **ADMISSIBLE** | -16.75 bp/unit (negative) |
| 6 | Macro regime overlay extension (`macroregime_001`) | 3.70 | +0.1110%/yr | +6.9222%/yr | +0.1110%/yr | 180.27 bp/unit | **ADMISSIBLE** | none (no cost level reaches the gate) |
| 10 | Intraday session / time-of-day effects (overnight variant, `overnight_capture_001`) | 504.00 | +15.1200%/yr | +9.1558%/yr | +15.1200%/yr | 1.74 bp/unit | **INADMISSIBLE** | +0.47 bp/unit (below the 3 bp/unit the model charges) |

### Rows with no derivable cost basis (four of the ten rows)

| Shortlist rank | Candidate | Why there is no cost basis | What stands in its place |
|---|---|---|---|
| 5 | TSMOM parameter variants | No separate candidate configuration exists to cost: the family is the incumbent's own parameter set, and the repository's own 100-configuration grid already rejected it on evidence (0/100 beat the baseline test Sharpe). | The incumbent's row (rank 1) is the family's cost basis; the variants are not re-costed because they were never evaluated as candidates. |
| 7 | Commodity/rate futures basis and roll yield | Front-month series now cached (`data/raw/{CL-F,NG-F,GC-F,ZB-F}.parquet`, 2015-01-02 .. 2026-10-15, 2,964-2,965 sessions, 0 missing closes, 0 duplicate dates) and the roll **dates** are now observable from the cached volume signature (Cycle 884), but the roll **price** is not: no source in scope serves the individual contract leg closes (nine source classes probed; expired legs 404, currently listed legs are chain aliases), so the roll spread and the roll cost actually paid remain unobservable. Hence no honest gross-return + turnover pair exists and no derivable turnover. | Blocked by data (unchanged verdict; see `research/reports/futures_basis_data_integrity_001.md`, `research/reports/futures_roll_visibility_001.md` and `research/experiments/futuresbasis_001.md`). |
| 8 | Crypto perpetual funding-rate carry | No crypto spot/perp or funding series is cached, so no return series and no weight path exist to cost. | Blocked by data (unchanged verdict). |
| 9 | Volatility risk premium | No **tradeable** volatility instrument is cached (^VIX is an index, not an executable return series), so no return series and no weight path exist to cost. | Blocked by data (unchanged verdict). |

Every row of the shortlist now carries a cost basis: six rows are costed from the committed
cache, and four are listed above with the reason they cannot be.

### What the completed column changes

* **The cost column does not promote any remaining candidate.** `csmomentum_001`,
  `sectorrotation_001` and `macroregime_001` are all **ADMISSIBLE** on cost — their gross signal
  is 62x to 141x what their own turnover requires — but that headroom is **survival, not edge**:
  all three are *below* the repository's 0.9 walk-forward gate before a single basis point is
  charged (canonical walk-forward mean OOS Sharpe 0.8458 / 0.8529 / 0.4733), their **gate
  headroom is negative** (they would have to be *paid* to trade to reach the gate), and their
  benchmark-parity cost is negative too, i.e. at zero cost they still do not match passive
  close-to-close holding of the same basket on the same folds.
* **The only candidate with real cost headroom is the incumbent** (+37.51 bp/unit, 12.5x the
  model's 3 bp/unit) — and even that is a statement about survival; its edge comes from its own
  walk-forward record, not from this screen.
* **The shortlist's ranking is left intact.** Cost-admissibility is a filter to apply *before*
  short-listing, not a re-ranking of the list.

Full evidence: `research/reports/cost_admissibility_screen_001.md` (Cycle 882); the record of the
cycle is `research/experiments/cost_admissibility_screen_001.md`.

---

## Candidate C1: TSMOM incumbent — tsmomentum_spytrend_001 (226d lookback, 21d skip, top-50%, vol-target 10%, DD control 15%, SPY 200d SMA filter)

**Category:** TSMOM variants
**Universe:** SPY, QQQ, IWM, TLT, GLD, EFA, EEM
**Mechanism:** Time-series momentum: assets with strong 12-month risk-adjusted performance continue to outperform; regime filter removes equity exposure in SPY downtrends.

**Evidence base:**
- Cycle 6 walk-forward (48 folds, fixed params): mean OOS Sharpe 0.9473, 91.7% positive folds, 6,013 pooled OOS trades
- SMA-window plateau: 6/6 windows (150-277d) >= 0.9 Sharpe
- Cycle 7 test period (2018-2026): Sharpe 1.4178, max DD -7.79%, 1,196 trades, 13.3x annualized turnover
- Cycle 8-10: paper-trading engine operational; 5-day track record (gate: 63 days)

### Scores

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| (a) Data quality/access | 5 (excellent / feasible) | All 7 universe ETFs cached with 8,482+ days of clean daily OHLCV (1993/1999-2026); 100% close completeness |
| (b) Structural mechanism | 4 (strong) | Well-documented anomaly with behavioral (underreaction) and institutional (slow diffusion) explanations; persistence debated due to competition |
| (c) Expected net return | 4 (strong) | Net of 3bps round-trip: walk-forward mean OOS Sharpe 0.9473 exceeds the 0.9 promotion gate; mean fold ann. return ~14.7% |
| (d) Robustness/statistical power | 4 (strong) | Plateau robust (6/6 windows) and 48-fold WF consistent; caveat: Cycle 3's 100-config grid shows the baseline on a parameter peak (5% within 0.05 Sharpe), so exact-parameter fragility is a documented risk |
| (e) Liquidity/capacity | 5 (excellent / feasible) | SPY/QQQ/IWM are among the most liquid ETFs globally; capacity far exceeds any realistic fund size |
| (f) Automation/operating burden | 5 (excellent / feasible) | Daily data, ~monthly signal horizon; engine, simulation, and paper-trading infrastructure all operational in-repo |
| (g) Diversification from existing research | 5 (excellent / feasible) | US equity multi-asset; uncorrelated with the existing large-cap crypto exposure |
| **Overall** | **32/35** | |

**Verdict: Credible candidate** — All promotion gates passed (WF mean OOS Sharpe >= 0.9, >= 50% positive folds, SMA plateau). Currently in prospective paper-trading validation.

---

## Candidate C3: Long-only cross-sectional momentum, broad 18-ETF universe

**Category:** Cross-sectional momentum
**Universe:** SPY, QQQ, IWM, TLT, GLD, DBC, VNQ, EFA, EEM, 9 sector ETFs (XLB-XLY)
**Mechanism:** Cross-sectional momentum: rank assets by intermediate-term return, hold the top fraction; leadership persistence across asset classes and sectors.

**Evidence base:**
- Full 18-ETF cache available (8,482 SPY days; sector ETFs 1998-2026)
- Untested in this repository — no prior backtest, no prior hypothesis doc
- Machinery exists: src/features/momentum.py rank_assets/select_top_decile

### Scores

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| (a) Data quality/access | 5 (excellent / feasible) | All 18 ETFs cached with 1993/1998-2026 daily history; no missing data; no fetch required |
| (b) Structural mechanism | 5 (excellent / feasible) | Cross-sectional momentum is a first-order, globally documented anomaly (Asness et al. 2013) with structural underreaction explanation |
| (c) Expected net return | 3 (adequate) | Untested — expected gross premia modest (low-to-mid single digits annualized for long-only form); net of 3bps costs plausible but unproven |
| (d) Robustness/statistical power | 3 (adequate) | Untested; ~28-33 years of daily data implies ~330-400 monthly rebalance observations, adequate but not yet validated; multiple-testing discipline required |
| (e) Liquidity/capacity | 5 (excellent / feasible) | All members are large, highly liquid ETFs |
| (f) Automation/operating burden | 4 (strong) | Ranking machinery already exists in-repo; monthly rebalancing; no short-side execution needed in long-only form |
| (g) Diversification from existing research | 4 (strong) | Different signal formation (cross-sectional rank vs incumbent's time-series-then-rank hybrid) and 2.5x broader universe; moderate diversification from incumbent research |
| **Overall** | **29/35** | |

**Verdict: Exploratory signal** — Data fully supports a valid chronological test; no prior evidence in-repo. Highest-ranked untested candidate — hypothesis formation and pre-registration is the natural next cycle.

---

## Candidate C4: Sector rotation (cross-sectional momentum across 9 GICS sector ETFs)

**Category:** Cross-sectional momentum
**Universe:** XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY
**Mechanism:** Sector leadership persists with the business cycle; rotating into leading sectors captures cyclical momentum and sector-specific underreaction.

**Evidence base:**
- 9 sector ETFs cached (1998-2026, 6,991 days each)
- Untested in this repository

### Scores

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| (a) Data quality/access | 5 (excellent / feasible) | All 9 sector ETFs cached, 1998-2026, complete daily OHLCV |
| (b) Structural mechanism | 4 (strong) | Sector rotation is a documented, structurally motivated effect (business-cycle leadership, staggered information diffusion across sectors) |
| (c) Expected net return | 3 (adequate) | Untested; concentrated 9-asset universe raises idiosyncratic risk; net-of-cost premia unproven |
| (d) Robustness/statistical power | 3 (adequate) | Untested; only 9 cross-sectional members limits rank signal richness; ~330 monthly observations |
| (e) Liquidity/capacity | 5 (excellent / feasible) | Sector ETFs are highly liquid |
| (f) Automation/operating burden | 4 (strong) | Same machinery as C3; slightly more monitoring (sector-specific event risk) |
| (g) Diversification from existing research | 4 (strong) | Sector-concentrated equity exposure; partially overlapping the incumbent's equity beta |
| **Overall** | **28/35** | |

**Verdict: Exploratory signal** — Valid test possible with cached data; subsumed by C3 if C3's broad universe is validated first (sector rotation is C3 restricted to 9 assets).

---

## Candidate C6: Calendar / rebalancing effects (month-end, quarter-end, index reconstitution flows)

**Category:** Rebalancing/calendar effects
**Universe:** Any cached ETF (SPY, QQQ, IWM primary)
**Mechanism:** Recurring institutional flows at month-end, quarter-end, and index reconstitution dates create predictable short-horizon price pressure.

**Evidence base:**
- Full daily history cached (8,482 SPY days) — calendar effects are directly computable
- Untested in this repository

### Scores

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| (a) Data quality/access | 5 (excellent / feasible) | Complete daily cache; calendar is deterministic and point-in-time safe |
| (b) Structural mechanism | 3 (adequate) | Documented in academic literature but effects are small, short-lived, and competed |
| (c) Expected net return | 2 (weak) | Expected effect is typically below the 3bps round-trip hurdle for daily-frequency capture; likely negative net edge without very low turnover design |
| (d) Robustness/statistical power | 3 (adequate) | Many observations available, but effect size is small relative to noise; high multiple-testing risk across calendar definitions |
| (e) Liquidity/capacity | 5 (excellent / feasible) | Large ETFs, no capacity constraint |
| (f) Automation/operating burden | 4 (strong) | Simple to implement; calendar rules deterministic |
| (g) Diversification from existing research | 4 (strong) | Equity-based, different mechanism from momentum; moderate diversification |
| **Overall** | **26/35** | |

**Verdict: Exploratory signal** — Valid test possible, but expected net edge is small relative to transaction costs; low priority. Must clear the cost hurdle to be credible.

---

## Candidate C2: TSMOM parameter variants (alternative lookback/skip/top-fraction combinations)

**Category:** TSMOM variants
**Universe:** SPY, QQQ, IWM, TLT, GLD, EFA, EEM
**Mechanism:** Same time-series momentum mechanism as C1 with different parameterizations.

**Evidence base:**
- Cycle 3 robustness grid (100 configurations): 0/100 beat the baseline test Sharpe (0.6445); 99 scored worse
- Only 5% of configurations within +/-0.05 Sharpe of baseline — baseline sits on a peak, not a plateau

### Scores

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| (a) Data quality/access | 5 (excellent / feasible) | Same cached data as C1 |
| (b) Structural mechanism | 4 (strong) | Same structural mechanism as C1 |
| (c) Expected net return | 2 (weak) | Empirically worse: every alternative configuration tested below baseline on the same period |
| (d) Robustness/statistical power | 2 (weak) | The 100-config grid shows the validated parameters are a local peak, not a plateau — variants are fragile by the repository's own evidence |
| (e) Liquidity/capacity | 5 (excellent / feasible) | Same liquid ETFs as C1 |
| (f) Automation/operating burden | 5 (excellent / feasible) | Same infrastructure as C1 |
| (g) Diversification from existing research | 2 (weak) | Zero incremental diversification — same strategy family, same assets |
| **Overall** | **25/35** | |

**Verdict: Rejected** — Variants tested strictly worse than the incumbent on identical data; no diversification value. The parameter-peak caveat is logged as a risk for the incumbent, not a reason to test variants.

---

## Candidate C5: Macro regime overlay extension (SPY 200d SMA + ^VIX regime indicators)

**Category:** Macro regime strategies
**Universe:** SPY, QQQ, IWM, TLT, GLD, EFA, EEM + ^VIX (regime input only)
**Mechanism:** Combine the incumbent's SPY trend filter with volatility-regime indicators (VIX level/trend) to reduce equity exposure in high-volatility regimes.

**Evidence base:**
- ^VIX cached: 8,502 days (1993-01-04 to 2026-10-08)
- SPY SMA regime filter already validated within the incumbent (Cycle 5)
- Untested as a multi-indicator overlay

### Scores

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| (a) Data quality/access | 4 (strong) | ^VIX index cached 1993-2026; but ^VIX is not tradeable, so only usable as a regime input, not a return series |
| (b) Structural mechanism | 4 (strong) | Volatility regimes are persistent (vol clustering) and VIX spikes lead equity drawdowns; structurally motivated |
| (c) Expected net return | 3 (adequate) | Untested; regime overlays typically improve consistency (Sharpe/DD) more than raw return; net effect unproven |
| (d) Robustness/statistical power | 3 (adequate) | Untested; high multiple-testing risk when adding regime indicators (regime definitions are researcher degrees of freedom) |
| (e) Liquidity/capacity | 3 (adequate) | As an overlay on the incumbent, capacity is unchanged; direct vol expression is impossible without a tradeable instrument |
| (f) Automation/operating burden | 4 (strong) | Daily data; overlay logic simple to implement on the existing engine |
| (g) Diversification from existing research | 3 (adequate) | Extends the incumbent strategy family — limited incremental diversification |
| **Overall** | **24/35** | |

**Verdict: Exploratory signal** — Testable only as an overlay on the incumbent (not standalone); ^VIX is an index, so no direct volatility exposure is executable from cache.

---

## Candidate C9: Commodity/rate futures basis and roll yield

**Category:** Basis/calendar spread
**Universe:** CL=F, NG=F, GC=F, ZB=F (front-month series now cached; the roll **dates** are observable from the cached volume signature, the roll **prices** are not — see `research/reports/futures_basis_data_integrity_001.md` and `research/reports/futures_roll_visibility_001.md`)
**Mechanism:** Roll yield from backwardation/contango and spot-futures basis convergence provide structural carry compensation.

**Evidence base:**
- Front-month series now cached (`data/raw/{CL-F,NG-F,GC-F,ZB-F}.parquet`, 2015-01-02 .. 2026-10-15, complete, 0 missing closes, 0 duplicate dates; aligned-frame SHA-256 `f898cd42...`)
- **Roll dates are observable** (Cycle 884): the cached `Volume` column is the front contract's volume, so the expiring contract's run-off and the new front's volume recovery mark each roll — 127/125/72/62 detected events for CL/NG/GC/ZB with modal spacings 29/30/63/91 days, matching each product's monthly / bi-monthly / quarterly contract cycle; the one independently verified roll (2026-09-23) is detected from the cache alone (`research/futures_roll_visibility.py`)
- **No point-in-time roll price constructible**: the two leg closes at the roll are still unobservable — nine source classes probed in Cycle 884 (Yahoo per-contract suffix symbols, Nasdaq Data Link CHRIS `CL1`/`CL2`, CME settlements, WSJ, Barchart, Stooq, FT Markets, Investing.com, Yahoo symbol search) and none serves individual contract legs; expired legs 404, currently listed legs are chain aliases
- No separate spot series for basis calculation

### Scores

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| (a) Data quality/access | 2 (weak) | Front-month series cached but no observable roll prices/legs; continuous-contract roll methodology undocumented, making a reproducible point-in-time backtest unreliable |
| (b) Structural mechanism | 4 (strong) | Roll yield and basis are structural features driven by storage, convenience yield, and hedging pressure |
| (c) Expected net return | 3 (adequate) | Roll yield is regime-dependent and can be negative for years (contango); net-of-roll-cost returns unproven |
| (d) Robustness/statistical power | 2 (weak) | Roll-timing ambiguity undermines any statistical test; no term-structure data cached |
| (e) Liquidity/capacity | 3 (adequate) | Front-month energy/metals futures are liquid; agriculture less so |
| (f) Automation/operating burden | 2 (weak) | Requires futures account, margin, and roll management — not supported by the daily-ETF engine |
| (g) Diversification from existing research | 5 (excellent / feasible) | Commodity/rate exposure would be strongly diversifying vs. existing crypto/equity research |
| **Overall** | **21/35** | |

**Verdict: Blocked by data** — Front-month series cached and the **roll dates are now observable** in the cached volume signature, but the roll **prices/legs** remain unobservable (nine source classes probed in Cycle 884), so the roll cost actually paid — and therefore any honest roll-yield return series — still cannot be built; no basis computable. Would need a source of individual contract leg closes first.

---

## Candidate C8: Crypto perpetual funding-rate carry (spot long + perp short)

**Category:** Carry/funding strategies
**Universe:** BTC/USDT, ETH/USDT perpetuals on OKX (not cached)
**Mechanism:** Perpetual swaps pay funding to anchor price to spot; persistently positive funding can be harvested via spot-long/perp-short.

**Evidence base:**
- Cycle 1 live verification: OKX accessible, ~66 days of 8h funding history, avg funding ~5.85% annualized (BTC)
- No crypto data cached in the repository
- Binance/Bybit geo-blocked (HTTP 451/403)

### Scores

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| (a) Data quality/access | 2 (weak) | Nothing cached; single accessible exchange (OKX); only ~66 days of verified funding history — insufficient for statistical power |
| (b) Structural mechanism | 4 (strong) | Funding is a mechanical perpetual-swap feature driven by leveraged long demand — structural, not data-mined |
| (c) Expected net return | 3 (adequate) | Verified ~5.85% annualized funding for BTC over 66 days, but rates are volatile and can turn negative; net of fees unproven |
| (d) Robustness/statistical power | 2 (weak) | 66 days is far below the 100-trade / multi-regime evidence bar; deep pagination would be required |
| (e) Liquidity/capacity | 5 (excellent / feasible) | BTC/ETH perp liquidity is deep (sub-1bps verified spreads) |
| (f) Automation/operating burden | 3 (adequate) | Requires real-time API, margin management across spot and swap accounts — heavier operational burden |
| (g) Diversification from existing research | 1 (poor / infeasible) | Existing research exposure is already large-cap crypto — zero diversification value |
| **Overall** | **20/35** | |

**Verdict: Blocked by data** — Insufficient verified funding-rate history (~66 days vs. multi-year requirement), single exchange, and zero diversification from existing crypto exposure.

---

## Candidate C7: Volatility risk premium (short volatility / variance premium capture)

**Category:** Volatility risk premium
**Universe:** Requires tradeable vol instrument (VIX futures, VXX/UVXY) — none cached
**Mechanism:** Option sellers earn a premium for bearing tail risk; short-vol strategies harvest the variance risk premium.

**Evidence base:**
- ^VIX index cached but NOT tradeable
- No VIX futures, VIX ETNs, or options history cached

### Scores

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| (a) Data quality/access | 2 (weak) | Only the ^VIX index is cached; no tradeable volatility instrument exists in the repository |
| (b) Structural mechanism | 4 (strong) | Variance risk premium is a structural, well-documented feature of options markets |
| (c) Expected net return | 2 (weak) | Not expressible with cached data; short-vol strategies carry severe negative skew |
| (d) Robustness/statistical power | 2 (weak) | No tradeable return series to test; any backtest would require synthetic or fetched data |
| (e) Liquidity/capacity | 2 (weak) | Tradeable vol instruments (when available) have capacity limits and decay risk |
| (f) Automation/operating burden | 2 (weak) | Requires futures/options infrastructure not present |
| (g) Diversification from existing research | 4 (strong) | Volatility exposure is largely uncorrelated with directional equity/crypto — good diversification in principle |
| **Overall** | **18/35** | |

**Verdict: Blocked by data** — No tradeable volatility instrument is cached or fetchable with history in this environment (^VIX is an index; VX=F not available from yfinance).

---

## Candidate C10: Intraday session / time-of-day effects (open-close patterns)

**Category:** Session/time-of-day effects
**Universe:** SPY, QQQ, IWM (requires intraday data)
**Mechanism:** Systematic patterns around the open and close auctions (overnight gaps, closing-auction liquidity).

**Evidence base:**
- No intraday history cached (all 19 raw files are daily)
- Cycle 1 live verification: only recent 1-day (1m) / 7-day (5m) windows available

### Scores

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| (a) Data quality/access | 1 (poor / infeasible) | No multi-year intraday data cached or fetchable; recent 1-7 day windows cannot support any statistical test |
| (b) Structural mechanism | 3 (adequate) | Auction-microstructure effects have some structural basis but are heavily arbitraged |
| (c) Expected net return | 2 (weak) | Typical overnight/intraday premia are small relative to 3bps+ round-trip costs including spread |
| (d) Robustness/statistical power | 1 (poor / infeasible) | Insufficient observations — statistically untestable with available data |
| (e) Liquidity/capacity | 4 (strong) | Large ETFs are liquid |
| (f) Automation/operating burden | 2 (weak) | Requires intraday data feeds and precise execution timing |
| (g) Diversification from existing research | 4 (strong) | Equity-based; moderate diversification in principle |
| **Overall** | **17/35** | |

**Verdict: Rejected** — Insufficient data for a valid test (no intraday history). Rejected per AGENTS.md: reject opportunities explained by bad data / infeasible execution.

---

## Price Predictability vs Executable Net Edge

The scoring explicitly separates *price predictability* (does a signal forecast returns in cached data?) from *executable net edge* (does the forecast survive costs, borrow, and operational friction?). Candidates C7-C10 fail on executability or data readiness regardless of any predictive content: no tradeable instrument (C7), insufficient history (C8), unobservable roll prices/legs (C9 — its roll *dates* are observable in the cached volume signature since Cycle 884, its leg closes are not), or no intraday data (C10). C2 fails on evidence: its own parameter grid shows the incumbent's parameters are a local peak, so variants are not independently supported. C1 is the only candidate with passed promotion gates; C3-C6 are untested but formable with cached data.

## Ranking & Recommendation

| Rank | Candidate | Overall | Verdict | Key Constraint |
|------|-----------|---------|---------|----------------|
| 1 | TSMOM incumbent | 32/35 | Credible candidate | Paper track record 5/63 days; parameter-peak caveat logged |
| 2 | Long-only cross-sectional momentum, broad 18-ETF universe | 29/35 | Exploratory signal | Untested — needs hypothesis pre-registration before any backtest |
| 3 | Sector rotation | 28/35 | Exploratory signal | Untested; subsumed by C3 if C3 validates first |
| 4 | Calendar / rebalancing effects | 26/35 | Exploratory signal | Expected effect below cost hurdle |
| 5 | TSMOM parameter variants | 25/35 | Rejected | Tested worse than incumbent on identical data |
| 6 | Macro regime overlay extension | 24/35 | Exploratory signal | Overlay only; ^VIX not tradeable; regime overfitting risk |
| 7 | Commodity/rate futures basis and roll yield | 21/35 | Blocked by data | Front-month cached; roll dates observable (volume signature, Cycle 884); roll prices/legs still unobservable |
| 8 | Crypto perpetual funding-rate carry | 20/35 | Blocked by data | ~66 days funding history; single exchange; no diversification |
| 9 | Volatility risk premium | 18/35 | Blocked by data | No tradeable volatility instrument |
| 10 | Intraday session / time-of-day effects | 17/35 | Rejected | No intraday history |

**Counts:** 1 credible candidate, 4 exploratory signals, 3 blocked by data, 2 rejected (10 total).

**Recommendation for Cycle 12:** Continue prospective paper-trading validation of C1 (incumbent; gate is 63 days of track record). The highest-ranked untested candidate is **C3 (long-only cross-sectional momentum on the broad 18-ETF cache)** at 29/35: data quality is maximal (fully cached, point-in-time safe), the structural mechanism is first-order, and it diversifies the incumbent's signal formation. Per AGENTS.md 'hypothesis first', Cycle 12 should document the C3 hypothesis and pre-register its evaluation plan (splits, benchmarks, promotion gates, multiple-testing controls) BEFORE any backtest execution.

---

*Report generated by `research/run_cycle11.py` (Cycle 11). Scores are structural pre-test assessments grounded in cached data and prior experiment records; they are not backtest results.*
