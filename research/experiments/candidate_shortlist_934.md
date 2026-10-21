# Experiment: Candidate shortlist (candidate_shortlist_934)

**Cycle 934.** Measurement and documentation cycle: **no** backtest was run,
**no** parameter was searched, **no** candidate was implemented, **no** gate, threshold,
decision mapping, universe, cost model, Sharpe convention, candidate configuration or
committed artifact was changed; nothing under `data/` or `config/` was written; the
fetcher was never called; no candidate was promoted, re-fit or re-ranked.

## Hypothesis reference

This is a **shortlist cycle**, not a candidate cycle. It has no hypothesis of its own.
Its inputs are the committed records of every earlier candidate line and the committed
cache and configuration, and its output is the selection of **one** mechanism for the
next cycle to pre-register.

## Data used

- **Source**: the committed parquet cache `data/raw/` (the fetcher is never called).
- **Files read by this cycle**: the nine GICS sector ETFs, the incumbent's seven-asset
  universe, the four front-month futures series and the commodity/ETF legs named by the
  candidates.
- **Frequency**: daily, session hours.
- **Point-in-time treatment**: this cycle measures **data availability**, not returns.
  No signal is formed, no weight is computed and no return is produced, so the cycle
  introduces no point-in-time exposure of its own. The point-in-time properties of the
  panels it measures are the committed findings (Cycle 929 membership audit; Cycle 884
  roll-date visibility).

## Configuration

| Item | Value | Source |
|---|---|---|
| Commission | 1.0 bp per unit of weight change | `config/settings.yaml` via `src.backtest.engine.get_cost_params()` |
| Slippage | 2.0 bp per unit of weight change | `config/settings.yaml` via `src.backtest.engine.get_cost_params()` |
| Round trip | 3.0 bp per unit of weight change | derived |
| Risk-free rate | 2.00% annual | `config/settings.yaml` via `src.backtest.engine.get_risk_free_rate()` |
| Turnover convention | 1.0 unit per rebalance | the committed cost-screen convention (`research/reports/opportunity_shortlist.md`: calendar_effects_001 24.13 units/yr for 24 rebalances; overnight-capture 504.00 units/yr for 504 sessions) |
| Trials | **1** per candidate -- no candidate carries a parameter grid | declared |

## Number of trials

**1.** The candidate set is a catalogue of four mechanisms, each with one declared
baseline rule. No parameter is searched and no candidate is executed in this cycle; the
four candidates are alternatives, not trials of one hypothesis.

## Results

### 1. The inventory that the scores rest on

**Data available** (1856 files under `data/`, 13 configuration files under `config/`, all read-only).

| Data class | Available in the cache | Consequence for this shortlist |
|---|---|---|
| Daily ETF OHLCV, constant cross-section | Yes -- the nine GICS sector ETFs carry an identical history (6991 sessions, 1998-12-22 .. 2026-10-08, no gaps) | The only membership-stable cross-section in the repository; the basis of `reversal_001`, `pairs_001` and `liquidity_001` |
| Daily ETF OHLCV, growing cross-section | Yes -- the incumbent's seven-asset universe gains members over the sample (Cycle 929) | Not used as a candidate universe here |
| Front-month futures | Yes -- CL-F, GC-F, NG-F, ZB-F from 2015-01-02; roll **dates** detectable, roll **prices** unobservable (Cycle 884) | The signal of `leadlag_001` is contaminated at every roll; CL-F carries a non-positive close inside the sample |
| Crypto spot/perp/funding | Yes (BTC/ETH, 2020-01-01 .. 2026-09-30) | Already closed: `cryptofunding_001` is an exploratory signal, not promoted |
| Intraday bars, options, borrow, VIX futures | **No** | No candidate below needs them, and no candidate below claims them |

**Cost model actually available**: 1.0 bp commission + 2.0 bp slippage = **3.0 bp per unit of weight change**, risk-free 2.00% annual. The friction components **absent** from the repository's cost model are: bid_ask_spread, borrow, roll, market_impact, latency, margin. A candidate that needs an absent friction is penalised on (a), (c) and (f), and the penalty is published with the candidate.

### 2. The lines that are already closed (quoted from the committed records)

A closed line is not reopened and no variant of it is proposed. The status of each line
is quoted from the committed record that carries it; the tool verifies that the quoted
text is still present in that file.

| Line | Committed record | Status class | Status line (verbatim) |
|---|---|---|---|
| `tsmomentum_spytrend_001 (incumbent)` | `research/experiments/tsmomentum_regime_filter_wf_001.md` | incumbent (Credible Candidate; NO-GO for promotion) | "## **Credible Candidate**" |
| `riskparity_001` | `research/experiments/riskparity_001_evaluation.md` | Rejected/Failed | "**Decision: REJECT (negative result).**" |
| `csmomentum_001` | `research/experiments/csmomentum_plateau_gate_eval_001.md` | Rejected/Failed | "- Research label: **Rejected/Failed**" |
| `sectorrotation_001 / sectorrotation_002` | `research/experiments/sectorrotation_002_experiment_001.md` | Rejected/Failed | "hypothesis FALSIFIED (Rejected/Failed)" |
| `calendar_effects_001` | `research/experiments/calendar_effects_baseline_wf_001.md` | Rejected/Failed | "**FINAL VERDICT:** Rejected/Failed" |
| `overnight_capture_001` | `research/experiments/overnight_capture_backtest_001.md` | Rejected/Failed | "**Rejected/Failed.**" |
| `macroregime_001` | `research/experiments/macroregime_001_experiment_002.md` | Rejected/Failed | "hypothesis FALSIFIED (Rejected/Failed)" |
| `cryptofunding_001` | `research/experiments/cryptofunding_002_evaluation.md` | Exploratory signal (not promoted) | "**Exploratory signal — not promoted.**" |
| `futuresbasis_001` | `research/experiments/futuresbasis_001.md` | Blocked by data/infrastructure | "**Blocked by data/infrastructure** (roll-price block)" |
| `futuresbasis_002` | `research/experiments/futuresbasis_002.md` | Rejected/Failed | "Verdict: Rejected/Failed on cost (and signal sign)." |
| `mom121_microcap_001` | `research/experiments/mom121_microcap_001.md` | Blocked by data/infrastructure | "**Status:** **Blocked by data/infrastructure** — data gate failed" |

### 3. The four candidates and their scores

Scoring legend (the repository's own): 1 = poor/infeasible, 2 = weak, 3 = adequate,
4 = strong, 5 = excellent/feasible; total = sum of (a)-(g), maximum 35. A score is
**rule-based** where it rests on a quantity measured from the committed cache, and a
**declared prior** where it is a judgement the repository cannot measure without
implementing the candidate. Every such prior is labelled in the candidate block.

| Rank | Candidate | (a) Data | (b) Mechanism | (c) Net after costs | (d) Robustness | (e) Liquidity | (f) Automation | (g) Diversification | Total |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `reversal_001` | 5 | 4 | 3 | 5 | 4 | 5 | 2 | **28** |
| 2 | `pairs_001` | 4 | 4 | 3 | 5 | 3 | 4 | 2 | **25** |
| 3 | `liquidity_001` | 5 | 3 | 2 | 3 | 4 | 5 | 2 | **24** |
| 4 | `leadlag_001` | 1 | 3 | 2 | 3 | 3 | 3 | 1 | **16** |

### 4. The measured inputs behind the rule-based scores

| Candidate | Sessions | Window | Turnover (units/yr) | Drag @3 bp/unit | Measured gross scale | Required capture | Hurdle | Observations | Effective independent bets | Median instrument $volume |
|---|---|---|---|---|---|---|---|---|---|---|
| `reversal_001` | 6991 | 1998-12-22 .. 2026-10-08 | 52.00 | 1.5600% | 77.8181%/yr | 2.0047% | 5/5 | 1398 | not applicable (one book) | $296,232,152 |
| `pairs_001` | 6991 | 1998-12-22 .. 2026-10-08 | 52.00 | 1.5600% | 69.6626%/yr | 2.2394% | 5/5 | 1398 | 4.96 | $296,232,152 |
| `liquidity_001` | 6991 | 1998-12-22 .. 2026-10-08 | 24.00 | 0.7200% | 73.4546%/yr | 0.9802% | 5/5 | 332 | not applicable (one book) | $296,232,152 |
| `leadlag_001` | 2960 | 2015-01-02 .. 2026-10-15 | 52.00 | 1.5600% | 30.1518%/yr | 5.1738% | 4/5 | 592 | 2.96 | $188,536,208 |

### 5. The candidate blocks

#### `reversal_001` -- Cross-sectional short-horizon reversal (weekly, long-only laggard tilt)

- **Family**: short-horizon reversal (liquidity-provision compensation)
- **Mechanism**: An asset that has fallen over the past week tends to revert over the following weeks. The move is driven by non-informational, liquidity-demanding order flow; the seller who provides liquidity is compensated by the subsequent reversal, and short-sale and rebalancing constraints make temporary price pressure persistent. The effect is the mirror image of the momentum family the repository has already tested, over a horizon one order of magnitude shorter (5 sessions against 226+21).
- **Universe**: XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY
- **Data files**: `data/raw/XLB.parquet`, `data/raw/XLE.parquet`, `data/raw/XLF.parquet`, `data/raw/XLI.parquet`, `data/raw/XLK.parquet`, `data/raw/XLP.parquet`, `data/raw/XLU.parquet`, `data/raw/XLV.parquet`, `data/raw/XLY.parquet`
- **Holding horizon**: 5 sessions (rebalanced 52 times per year)
- **Baseline rule**: Rank the nine sector ETFs by the trailing 5-session total return; hold the bottom quintile (2 of 9) at equal weight and cash otherwise; rebalance every 5th session; the signal formed at t is effective at t+1 (one-session lag).
- **Benchmark**: 1/N equal-weight buy-and-hold of the same nine sector ETFs over the same window (the same benchmark the committed cross-sectional candidates use).
- **Cost model**: 1.5600%/yr (52.00 units of turnover at 3 bp/unit); friction components absent from the repository's cost model: none
- **Known confounders**: (1) Momentum-crash risk: the book is long the laggards, so a sharp rally in the recent winners is a direct loss. (2) The nine ETFs are all US equity sectors: the rule is a short-beta tilt against the 1/N benchmark in a risk-on market, so the benchmark-relative result, not the absolute return, is the relevant statistic. (3) The sector panel ends 2026-10-08, eight sessions behind the rest of the committed cache. (4) Constituent-level (GICS) membership history is not in the repository: the sector ETFs' underlying composition changed over the sample and cannot be reconstructed. (5) ETF expense ratios are embedded in the observed (adjusted) prices and are not modelled separately. (6) The turnover estimate of one book rotation per rebalance follows the repository's committed cost-screen convention and is an upper bound; a partial rotation turns over less.
- **Falsification condition**: Falsified if ANY of: (i) the walk-forward mean OOS Sharpe (net, canonical convention) < 0.9; (ii) the benchmark-relative net excess has a moving-block bootstrap 95% CI that includes zero; (iii) the benchmark-relative net excess is not positive in the post-2009 sub-sample; (iv) the measured gross capture fraction falls below the pre-registered cost hurdle; (v) the positive-fold rate < 0.5 or the pooled OOS trades <= 100.

| Dimension | Score | Basis (measured where measurable) |
|---|---|---|
| (a) Data quality/access | 5 | coverage 27.8y (>= 20 years) |
| (b) Plausible structural explanation | 4 | declared prior: The mechanism (compensation for supplying liquidity to non-informational order flow) is structural and documented; it is not rated 5 because the effect is heavily arbitraged in liquid ETFs and its published magnitude has decayed. |
| (c) Expected return after costs | 3 | cost hurdle 2.0047% of the measured gross scale -> hurdle 5/5; declared gross prior 3/5; score = min = 3 |
| (d) Robustness / statistical power | 5 | 1398 non-overlapping holding-horizon observations (>= 1000); effective-bet count not applicable (one book, one signal) |
| (e) Liquidity / capacity | 4 | median instrument $296,232,152/day (>= $250m/day) |
| (f) Automation / operating burden | 5 | declared prior: daily bars, one venue, session hours |
| (g) Diversification from existing research | 2 | mechanism-family novelty 5/5 (no committed candidate hypothesis in this family); instrument overlap with 3 closed line(s) -> exposure score 2/5; shared: csmomentum_001, sectorrotation_001, sectorrotation_002 |

**Total: 28 / 35**

#### `pairs_001` -- Cointegrated-pairs relative value (market-neutral dispersion convergence)

- **Family**: statistical arbitrage / spread convergence
- **Mechanism**: Two securities that share a common driver trade with a temporary dispersion around their long-run relationship; the dispersion reverts, and a market-neutral book (long the cheap leg, short the rich leg) earns the convergence without the common factor.
- **Universe**: XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY
- **Data files**: `data/raw/XLB.parquet`, `data/raw/XLE.parquet`, `data/raw/XLF.parquet`, `data/raw/XLI.parquet`, `data/raw/XLK.parquet`, `data/raw/XLP.parquet`, `data/raw/XLU.parquet`, `data/raw/XLV.parquet`, `data/raw/XLY.parquet`
- **Holding horizon**: 5 sessions (rebalanced 52 times per year)
- **Baseline rule**: For each of the six pre-registered pairs, z-score the log price ratio over the trailing 126 sessions and take the contrarian side when |z| >= 1; dollar-neutral per pair; rebalance every 5th session; the signal formed at t is effective at t+1.
- **Benchmark**: Cash (a market-neutral book; the repository's 2% risk-free rate is the hurdle).
- **Cost model**: 1.5600%/yr (52.00 units of turnover at 3 bp/unit); friction components absent from the repository's cost model: borrow cost / short availability: no borrow or short-side cost exists anywhere in config/ or data/
- **Known confounders**: (1) Short-sale constraints and recall risk are not modelled: the repository has no borrow cost at all. (2) Pair-selection multiplicity: six pairs are pre-registered, and the spread correlations are high, so the six bets are far from independent. (3) Structural breaks in the long-run relationship (a pair that stops being cointegrated) turn a convergence trade into a value trap. (4) The market-neutral construction must be funded and pays the repository's 2% risk-free rate, which the canonical Sharpe convention does not net.
- **Falsification condition**: Falsified if ANY of: (i) the walk-forward mean OOS Sharpe < 0.9; (ii) the net excess over cash has a moving-block bootstrap 95% CI that includes zero after deflating for the six pairs tested; (iii) the cointegration of any pair fails out of sample; (iv) the net excess does not survive a borrow cost of 25 bp per unit of short notional per rebalance.

| Dimension | Score | Basis (measured where measurable) |
|---|---|---|
| (a) Data quality/access | 4 | coverage 27.8y (>= 20 years); -1: required execution input absent (borrow cost / short availability: no borrow or short-side cost exists anywhere in config/ or data/) |
| (b) Plausible structural explanation | 4 | declared prior: Cointegration-driven convergence is a structural mechanism with a clear economic story (common driver, temporary liquidity-driven dispersion). |
| (c) Expected return after costs | 3 | cost hurdle 2.2394% of the measured gross scale -> hurdle 5/5; declared gross prior 3/5; score = min = 3 |
| (d) Robustness / statistical power | 5 | 1398 non-overlapping holding-horizon observations (>= 1000); 4.96 effective independent bets |
| (e) Liquidity / capacity | 3 | median instrument $296,232,152/day (>= $250m/day); -1: short leg required; borrow availability is not observable in the cache |
| (f) Automation / operating burden | 4 | declared prior: daily bars, one venue, session hours; -1: short leg (borrow, locate, recall handling) |
| (g) Diversification from existing research | 2 | mechanism-family novelty 5/5 (no committed candidate hypothesis in this family); instrument overlap with 3 closed line(s) -> exposure score 2/5; shared: csmomentum_001, sectorrotation_001, sectorrotation_002 |

**Total: 25 / 35**

#### `liquidity_001` -- Liquidity-provision premium (Amihud illiquidity tilt, long-only)

- **Family**: liquidity provision / illiquidity premium
- **Mechanism**: Assets whose price moves more per unit of traded volume earn a premium, because the liquidity provider is compensated for the risk of adverse selection; the premium is realised as the illiquid asset's price drifts back toward its fundamental value.
- **Universe**: XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY
- **Data files**: `data/raw/XLB.parquet`, `data/raw/XLE.parquet`, `data/raw/XLF.parquet`, `data/raw/XLI.parquet`, `data/raw/XLK.parquet`, `data/raw/XLP.parquet`, `data/raw/XLU.parquet`, `data/raw/XLV.parquet`, `data/raw/XLY.parquet`
- **Holding horizon**: 21 sessions (rebalanced 24 times per year)
- **Baseline rule**: Score each sector ETF by the Amihud measure |21-session return| / dollar volume over the trailing 21 sessions; hold the most illiquid quintile (2 of 9) at equal weight and cash otherwise; rebalance monthly; the signal formed at t is effective at t+1.
- **Benchmark**: 1/N equal-weight buy-and-hold of the same nine sector ETFs over the same window.
- **Cost model**: 0.7200%/yr (24.00 units of turnover at 3 bp/unit); friction components absent from the repository's cost model: none
- **Known confounders**: (1) The Amihud score is dominated by the volume denominator, so the ranking partly re-ranks the volume of the ETF wrappers, not the liquidity of the underlying sector. (2) Volume-based scores are sensitive to the volume spike that follows a large price move, which mechanically inverts the signal. (3) ETF volume is venue-fragmented and the cached volume is a consolidated daily figure. (4) Sector ETF expense ratios and index-tracking differences are embedded in the observed prices.
- **Falsification condition**: Falsified if ANY of: (i) the walk-forward mean OOS Sharpe < 0.9; (ii) the benchmark-relative net excess has a moving-block bootstrap 95% CI that includes zero; (iii) the measured cross-sectional dispersion of the Amihud score is too small to support a tilt that covers the 3 bp/unit cost model (the mechanism does not reach the hurdle); (iv) the net excess is not positive in the post-2009 sub-sample.

| Dimension | Score | Basis (measured where measurable) |
|---|---|---|
| (a) Data quality/access | 5 | coverage 27.8y (>= 20 years) |
| (b) Plausible structural explanation | 3 | declared prior: The mechanism is structural and well documented, but it is a premium of illiquidity, and the candidate's universe is the most liquid corner of the market: the mechanism is weak by construction here. |
| (c) Expected return after costs | 2 | cost hurdle 0.9802% of the measured gross scale -> hurdle 5/5; declared gross prior 2/5; score = min = 2 |
| (d) Robustness / statistical power | 3 | 332 non-overlapping holding-horizon observations (>= 250); effective-bet count not applicable (one book, one signal) |
| (e) Liquidity / capacity | 4 | median instrument $296,232,152/day (>= $250m/day) |
| (f) Automation / operating burden | 5 | declared prior: daily bars, one venue, session hours |
| (g) Diversification from existing research | 2 | mechanism-family novelty 5/5 (no committed candidate hypothesis in this family); instrument overlap with 3 closed line(s) -> exposure score 2/5; shared: csmomentum_001, sectorrotation_001, sectorrotation_002 |

**Total: 24 / 35**

#### `leadlag_001` -- Futures-to-ETF delayed price discovery (next-session lead-lag)

- **Family**: delayed price discovery / cross-instrument lead-lag
- **Mechanism**: The futures market is deeper and is quoted with a settlement convention that differs from the ETF's closing auction; information that reaches the futures close is only partly incorporated into the ETF close, so part of the futures move is realised in the ETF on the next session.
- **Universe**: CL-F, GC-F, NG-F, ZB-F, USO, BNO, UNG, GSG, GLD, TLT
- **Data files**: `data/raw/CL-F.parquet`, `data/raw/GC-F.parquet`, `data/raw/NG-F.parquet`, `data/raw/ZB-F.parquet`, `data/raw/USO.parquet`, `data/raw/BNO.parquet`, `data/raw/UNG.parquet`, `data/raw/GSG.parquet`, `data/raw/GLD.parquet`, `data/raw/TLT.parquet`
- **Holding horizon**: 5 sessions (rebalanced 52 times per year)
- **Baseline rule**: For each of the five pre-registered futures-to-ETF pairs, take the sign of the futures contract's trailing 5-session return as the signal for the ETF leg; long the ETF when the signal is positive and hold cash otherwise; rebalance every 5th session; the signal formed at t is effective at t+1.
- **Benchmark**: Cash (the rule is a directional tilt on the ETF leg only).
- **Cost model**: 1.5600%/yr (52.00 units of turnover at 3 bp/unit); friction components absent from the repository's cost model: roll price / roll cost: the cached front-month series exposes the roll date but not the roll price, so the futures return series is contaminated at every roll
- **Known confounders**: (1) The cached front-month futures series is a continuous series whose roll price is unobservable: the return series is contaminated at every roll event, so roll windows must be excluded, which removes part of the sample. (2) The committed roll detector classifies a session using up to eight forward sessions and four subsequent volume ratios, so the roll dates are an EX-POST detection: they can be used to clean a backtest but are not a tradable point-in-time signal, and any live rule would have to detect the roll with the same lag. (3) CL-F carries a non-positive close inside the sample (the front month went negative in 2020), which breaks any return computation that spans it. (4) The futures and the ETF legs have different trading calendars, so the paired panel is only complete on the sessions both markets opened. (5) The daily bar cannot establish the intraday ordering between the futures settlement and the ETF close, so the 'lead' is only testable in its weaker next-session form. (6) The four futures are four different factor exposures (oil, gas, gold, rates), so the five pairs are not independent bets.
- **Falsification condition**: Falsified if ANY of: (i) the walk-forward mean OOS Sharpe < 0.9; (ii) the net excess over cash has a moving-block bootstrap 95% CI that includes zero after deflating for the five pairs tested; (iii) the excess disappears once the detected roll windows are excluded, which would show the effect is a roll artefact; (iv) the excess is carried by the CL-F window, whose non-positive close makes the sample unusable.

| Dimension | Score | Basis (measured where measurable) |
|---|---|---|
| (a) Data quality/access | 1 | coverage 11.8y (>= 10 years); -1: cross-section is not constant (51.5% of sessions); -1: 1 integrity defect rows in the required series; -1: required execution input absent (roll price / roll cost: the cached front-month series exposes the roll date but not the roll price, so the futures return series is contaminated at every roll) |
| (b) Plausible structural explanation | 3 | declared prior: The mechanism is one AGENTS.md names explicitly (delayed price discovery), but the daily-bar cache cannot time the intraday sequencing that the mechanism depends on. |
| (c) Expected return after costs | 2 | cost hurdle 5.1738% of the measured gross scale -> hurdle 4/5; declared gross prior 2/5; score = min = 2 |
| (d) Robustness / statistical power | 3 | 592 non-overlapping holding-horizon observations (>= 500); -1: only 2.96 effective independent bets |
| (e) Liquidity / capacity | 3 | median instrument $188,536,208/day (>= $50m/day) |
| (f) Automation / operating burden | 3 | declared prior: daily bars, one venue, session hours; -1: front-month futures series (roll windows to detect and exclude); -1: more than nine instruments to maintain |
| (g) Diversification from existing research | 1 | mechanism-family novelty 5/5 (no committed candidate hypothesis in this family); instrument overlap with 5 closed line(s) -> exposure score 1/5; shared: tsmomentum_001, riskparity_001, csmomentum_001, macroregime_001, futuresbasis_002 |

**Total: 16 / 35**

### 6. Selection

**Declared selection rule** (fixed before the scores were read): the candidate with the
highest total wins; ties are broken by (a) data quality, then (c) expected return after
costs, then the candidate id in alphabetical order.

| Rank | Candidate | (a) Data | (b) Mechanism | (c) Net after costs | (d) Robustness | (e) Liquidity | (f) Automation | (g) Diversification | Total |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `reversal_001` | 5 | 4 | 3 | 5 | 4 | 5 | 2 | **28** |
| 2 | `pairs_001` | 4 | 4 | 3 | 5 | 3 | 4 | 2 | **25** |
| 3 | `liquidity_001` | 5 | 3 | 2 | 3 | 4 | 5 | 2 | **24** |
| 4 | `leadlag_001` | 1 | 3 | 2 | 3 | 3 | 3 | 1 | **16** |

**Selected: `reversal_001` -- Cross-sectional short-horizon reversal (weekly, long-only laggard tilt)** (total 28/35, next best `pairs_001` at 25/35, margin 3).

Why it wins, in the measured terms: it is the only candidate that combines a
membership-stable, gap-free 27.8-year cross-section (a = 5), a
weekly rebalance whose cost hurdle is a measured
2.0047% of the measured gross scale
(c = 3, the minimum of that hurdle and a declared gross prior of
3), 1398 non-overlapping
observations (d = 5), a median instrument turnover of
$296,232,152 per day
(e = 4), no short leg, no roll and no intraday data
(f = 5), and a mechanism family that no committed candidate
hypothesis has implemented (g = 2).

**The published weakness of the selection** (stated, not smoothed over): the nine-sector
panel is **not** new to this repository. Two rejected momentum lines
(`sectorrotation_001`, `sectorrotation_002`) and one rejected broad cross-sectional
momentum line (`csmomentum_001`) already traded it, so the (g) exposure score is
2/5 even though the mechanism itself is new. The next cycle must
therefore test the reversal signal against the **mirror** of the rejected sector
momentum signal on the same panel, so that "the opposite of a rejected hypothesis" is
not mistaken for a new edge.

### 7. The selected candidate's pre-registration skeleton

The next cycle pre-registers this candidate as `research/hypotheses/reversal_001.md` plus
`config/reversal_candidate_001.yaml` **before** any backtest is executed. The skeleton
below is the material that pre-registration must contain.

| Field | Value |
|---|---|
| **Mechanism** | An asset that has fallen over the past week tends to revert over the following weeks. The move is driven by non-informational, liquidity-demanding order flow; the seller who provides liquidity is compensated by the subsequent reversal, and short-sale and rebalancing constraints make temporary price pressure persistent. The effect is the mirror image of the momentum family the repository has already tested, over a horizon one order of magnitude shorter (5 sessions against 226+21). |
| **Expected direction** | Positive relative to the 1/N benchmark of the same nine sectors. **Magnitude: not measured in this repository.** The pre-registered cost hurdle is that the rule must capture at least 2.0047% of the measured cross-sectional dispersion per rebalance (77.8181%/yr of scale against a 1.5600%/yr drag) to break even at the repository's cost model. |
| **Holding horizon** | 5 sessions; rebalanced 52 times per year; the signal formed at t is effective at t+1 (one-session lag) |
| **Asset universe** | XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY (nine GICS sector ETFs; identical cached history, 6991 sessions, 1998-12-22 .. 2026-10-08, no gaps) |
| **Features and data sources** | `data/raw/XLB.parquet`, `data/raw/XLE.parquet`, `data/raw/XLF.parquet`, `data/raw/XLI.parquet`, `data/raw/XLK.parquet`, `data/raw/XLP.parquet`, `data/raw/XLU.parquet`, `data/raw/XLV.parquet`, `data/raw/XLY.parquet` -- committed parquet cache, daily OHLCV, the fetcher is never called |
| **Entry / exit rules** | Rank the nine sector ETFs by the trailing 5-session total return; hold the bottom quintile (2 of 9) at equal weight and cash otherwise; rebalance every 5th session; the signal formed at t is effective at t+1 (one-session lag). |
| **Benchmark** | 1/N equal-weight buy-and-hold of the same nine sector ETFs over the same window (the same benchmark the committed cross-sectional candidates use). |
| **Known confounders** | (1) Momentum-crash risk: the book is long the laggards, so a sharp rally in the recent winners is a direct loss. (2) The nine ETFs are all US equity sectors: the rule is a short-beta tilt against the 1/N benchmark in a risk-on market, so the benchmark-relative result, not the absolute return, is the relevant statistic. (3) The sector panel ends 2026-10-08, eight sessions behind the rest of the committed cache. (4) Constituent-level (GICS) membership history is not in the repository: the sector ETFs' underlying composition changed over the sample and cannot be reconstructed. (5) ETF expense ratios are embedded in the observed (adjusted) prices and are not modelled separately. (6) The turnover estimate of one book rotation per rebalance follows the repository's committed cost-screen convention and is an upper bound; a partial rotation turns over less. |
| **Falsification condition** | Falsified if ANY of: (i) the walk-forward mean OOS Sharpe (net, canonical convention) < 0.9; (ii) the benchmark-relative net excess has a moving-block bootstrap 95% CI that includes zero; (iii) the benchmark-relative net excess is not positive in the post-2009 sub-sample; (iv) the measured gross capture fraction falls below the pre-registered cost hurdle; (v) the positive-fold rate < 0.5 or the pooled OOS trades <= 100. |
| **Cost model assumptions** | 1.0 bp commission + 2.0 bp slippage = 3.0 bp per unit of weight change, applied to the absolute weight change on rebalance days; risk-free 2.00% annual for the Sharpe convention; no borrow (the rule is long-only), and **no** market-impact, spread, latency or margin term exists in the repository's cost model -- a disclosed gap, bounded by the committed Cycle-913 break-even audit; turnover estimated at 52.00 units/yr (1.5600%/yr drag) under the committed one-book-rotation-per-rebalance convention |

### 8. What this cycle deliberately does **not** propose

- **No risk-parity candidate and no risk-parity variant.** `riskparity_001` is closed
  (`research/experiments/riskparity_001_evaluation.md`: "**Decision: REJECT (negative
  result).**") and the family is not reopened here.
- **No reopened closed line.** Every line in the table of section 2 keeps its committed
  status; no variant of the momentum, sector-rotation, calendar, overnight, macro-regime,
  crypto-carry, futures-basis or microcap families is proposed.
- **No parameter search, no candidate implementation and no backtest.** The cycle
  measures availability and scores; it does not test any of the four candidates.
- **No change to `data/` or `config/`.** The run fingerprints every file under both
  trees before and after and fails closed if either changed.

## Decision

**Next task (Cycle 935): pre-register `reversal_001`** -- write
`research/hypotheses/reversal_001.md` and `config/reversal_candidate_001.yaml` with the
mechanism, horizon, universe, benchmark, confounders, falsification condition and cost
model above, **before** any backtest is executed, and then run the config-faithful
walk-forward on the nine-sector panel with the repository's committed cost model and
the 10y/12m/6m design with 21-day purge and embargo, reporting the benchmark-relative
net excess, its moving-block bootstrap CI, the mirror test against the rejected sector
momentum signal, and the capture fraction against the cost hurdle.

**Label of this cycle: shortlist produced, one candidate selected, nothing tested.** No
candidate's verdict changes; the incumbent stays a **Credible Candidate** by its
published verdict and **NO-GO** for promotion.

## Reproduction commands

```bash
python research/candidate_shortlist_934.py
python -m pytest -q tests/test_candidate_shortlist_934.py
git status --porcelain data/ config/
```
