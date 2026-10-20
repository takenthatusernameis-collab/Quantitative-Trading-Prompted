# Experiment: cryptofunding_002 — multi-year crypto funding history from the Binance public archive

Hypothesis: research/hypotheses/cryptofunding_001.md
Trials: 1 (data collection; no parameter grid, no strategy evaluation).

## Objective of this cycle

Close the Cycle 888 data blocker for shortlist rank 8 (`cryptofunding_001`): obtain **>= 1 year of
8h funding-rate history** for BTC/ETH USDT-margined perpetuals from an accessible free/public
source, plus a coupled spot price series, so that a reproducible spot-long/perp-short return path
can be built.

## Verdict

**Data blocker RESOLVED.** 2,464.7 days (6.75 years) of 8h funding history per symbol are cached
and checksum-verified, with a coupled daily spot/perp pair. The candidate's *data* status moves
from "Blocked by data" to "Exploratory signal" (testable, untested). **No edge is claimed**: no
fee, slippage, margin or funding-rounding cost has been applied, and no walk-forward split or
promotion-gate test has been run.

## Why the earlier route failed and what was used instead

* The OKX public funding-rate-history endpoint (Cycle 888) returns only ~296 records (~98.3 days)
  per symbol; it cannot be paged further.
* The live Binance REST API (`fapi.binance.com`) returns **HTTP 451** ("Service unavailable from a
  restricted location") and Bybit returns **HTTP 403** from this environment.
* The **Binance public data archive** (`https://data.binance.vision`) *is* reachable and publishes
  monthly ZIPs for perpetual funding rates and for klines, each with a companion `.CHECKSUM` file
  containing the ZIP's SHA256. That archive is the source used here.

## Data used

| Dataset | Source | Universe | Frequency | Range | Rows | Integrity |
|---|---|---|---|---|---|---|
| `data/raw/crypto/BTC_USDT_USDT_funding_binance.parquet` | Binance public archive, `data/futures/um/monthly/fundingRate/BTCUSDT/` | BTCUSDT USDT-margined perp | 8h | 2020-01-01T00:00:00Z .. 2026-09-30T16:00:00Z | 7,395 | 81/81 archive objects SHA256-verified |
| `data/raw/crypto/ETH_USDT_USDT_funding_binance.parquet` | same, `.../ETHUSDT/` | ETHUSDT USDT-margined perp | 8h | 2020-01-01T00:00:00Z .. 2026-09-30T16:00:00Z | 7,395 | 81/81 verified |
| `data/raw/crypto/{BTC,ETH}USDT_perp_1d_binance.parquet` | `data/futures/um/monthly/klines/{sym}/1d/` | USDT-margined perp | daily (UTC) | 2020-01-01 .. 2026-09-30 | 2,465 | 81/81 verified |
| `data/raw/crypto/{BTC,ETH}USDT_spot_1d_binance.parquet` | `data/spot/monthly/klines/{sym}/1d/` | spot | daily (UTC) | 2020-01-01 .. 2026-09-30 | 2,465 | 81/81 verified |
| `data/raw/crypto/{BTC,ETH}_USDT_USDT_funding.parquet` | OKX public API (Cycle 888) | USDT-SWAP | 8h | 2026-07-13 .. 2026-10-20 | 296 | kept as an independent cross-check |

Schema of the funding parquet matches the Cycle 888 OKX cache exactly: `timestamp` (epoch ms,
int64), `datetime` (UTC), `fundingRate` (float64), `symbol` (ccxt unified, e.g. `BTC/USDT:USDT`),
plus the archive's own `funding_interval_hours` column.

Machine-readable provenance (row counts, coverage, interval counts, gap list, per-file SHA256):
`research/reports/binance_crypto_manifest.json`.

### Point-in-time and integrity treatment

* Funding and price observations are keyed by their **settlement/open timestamp in UTC**; nothing
  is forward-filled, and no observation is carried across a gap. Funding is a settlement
  (cash-flow) event, not a forward-looking price, so it is used only on its own timestamp.
* Every archive object is verified against the published `.CHECKSUM` **before** parsing; a mismatch
  aborts the run and no output file is written.
* Archive timestamps carry a few milliseconds of jitter (e.g. `...002`). Timestamps are stored
  as epoch milliseconds and the jitter is treated as sub-second noise, not as a gap
  (gap tolerance 60 s).
* Spot klines from 2025-01 onwards are published in **microseconds**; the epoch unit is detected
  per file from the column magnitude, not assumed (`_epoch_ms`).
* Monthly klines files from 2025 onwards ship a **header row**; it is stripped before parsing.
* Duplicate settlement timestamps: 0. Missing 8h periods: **0**. Gap count (> 8h + 60 s): **0**.
* Universe membership is not a survivorship issue here: BTC and ETH are perpetual contracts, not
  listed equities — there is no point-in-time membership set to reconstruct.

## Cross-venue validation (independent check of the new series)

The Binance series is compared against the OKX series collected separately in Cycle 888 on their
overlapping 8h settlement window (2026-07-14 .. 2026-09-30, BTC):

| Statistic | Value |
|---|---|
| Overlapping 8h periods | 238 (2026-07-13 16:00Z .. 2026-09-30 16:00Z, aligned to the hour; 126 of them match on the exact settlement timestamp) |
| Correlation of funding rates | 0.518 |
| Same funding sign | 91.2% of periods |
| Median absolute difference | 0.213 bp per 8h (mean 0.253 bp) |
| Mean funding | 0.580 bp/8h (Binance) vs 0.515 bp/8h (OKX) |

The two independently sourced venues agree in sign for 91.2% of periods with sub-basis-point
level differences, which is the expected cross-venue dispersion and confirms the archived series
is genuine funding data rather than a malformed file.

## Reproducible construction path (spot long + perp short)

Implemented in `research/collect_binance_crypto_funding.py`
(`build_carry_path`, `carry_path_stats`), output committed to
`data/processed/crypto/{BTCUSDT,ETHUSDT}_carry_path.parquet` (2,464 daily rows per symbol,
2020-01-02 .. 2026-09-30). Definition, per UTC day:

```
funding_cashflow   = sum of the day's 8h funding rates credited to the short perp leg
spot_return        = spot_close[t] / spot_close[t-1] - 1
perp_return        = perp_close[t] / perp_close[t-1] - 1
basis_convergence  = spot_return - perp_return          (pair P&L when the perp converges)
gross_carry        = funding_cashflow + basis_convergence
basis_close        = perp_close / spot_close - 1
```

Funding is attributed to the UTC day of its settlement timestamp — the only convention the archive
supports (it publishes settlement times, not accrual windows).

### Gross (cost-free) descriptive results

| Symbol | Gross carry annualized | Funding annualized | Basis convergence annualized | Positive days |
|---|---|---|---|---|
| BTCUSDT | +11.59%/yr | +11.73%/yr | -0.14%/yr | 77.5% |
| ETHUSDT | +13.57%/yr | +13.84%/yr | -0.27%/yr | 76.6% |

Per-year gross carry (BTC / ETH, annualized): 2020 +16.5% / +26.2%; 2021 +30.6% / +37.3%;
2022 +4.1% / +0.7%; 2023 +7.7% / +8.1%; 2024 +12.0% / +13.0%; 2025 +5.1% / +4.9%;
2026 (Jan-Sep) +2.9% / +1.9%.

**These are gross, before costs, and are not an edge.** They are heavily regime-dependent
(+37.3%/yr in 2021, +1.9%/yr in 2026 YTD), the 2020-2021 window is a bull-market funding regime
that may not persist, and the pair pays fees on both legs plus margin and funding rounding.
Funding was negative in 13.9% of BTC periods and 13.8% of ETH periods over the full span.

## Limitations

* Single venue for the price legs (Binance); the OKX series is funding-only and is used as a
  cross-check, not as an independent price path.
* The archive publishes monthly files only through **2026-09** (no October-2026 file exists yet),
  so the series ends 2026-09-30 while the OKX cache runs to 2026-10-20.
* Daily close-to-close legs cannot see intra-day funding accrual timing or intra-day basis
  moves; a dollar-neutral pair held constant is assumed, with no rebalancing drift modelled.
* No fee schedule, slippage model, margin/financing cost or funding-rounding rule has been
  applied. The repository's own cost screen (`research/cost_admissibility_screen.py`) has no row
  for this candidate.

## Reproduction

```bash
python research/collect_binance_crypto_funding.py --construct-path   # re-download + rebuild
python research/collect_binance_crypto_funding.py --offline --construct-path  # rebuild from cache
python -m pytest -q tests/test_binance_crypto_funding.py              # invariants + cross-venue check
```

The collector caches the downloaded ZIPs under `data/raw/crypto/_cache/` (git-ignored) and
re-verifies each cached object's SHA256 against the archive's published `.CHECKSUM`, so
`--offline` runs are byte-identical to a fresh download.
