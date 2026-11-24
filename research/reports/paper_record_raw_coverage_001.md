# Paper record vs committed raw-cache coverage

Read-only audit produced by `research/paper_record_raw_coverage_audit.py`.
No file under `data/` or `config/` is written; values are re-derived from the
committed state and cache.

## Coverage

| quantity | value |
|---|---|
| universe checked | `SPY`, `QQQ`, `IWM`, `TLT`, `GLD`, `EFA`, `EEM` |
| committed raw coverage end (min across universe) | `2026-11-10` |
| record window | `2025-01-02` .. `2026-11-24` |
| record sessions | `476` |
| sessions covered by committed raw | `466` |
| sessions **not** re-derivable from `data/raw` | `10` |
| of those, attested by a provider digest | `4` |

Per-symbol last committed session:

| symbol | last session |
|---|---|
| `EEM` | `2026-11-10` |
| `EFA` | `2026-11-10` |
| `GLD` | `2026-11-10` |
| `IWM` | `2026-11-10` |
| `QQQ` | `2026-11-10` |
| `SPY` | `2026-11-10` |
| `TLT` | `2026-11-10` |

Unverified record sessions:
  - 2026-11-11
  - 2026-11-12
  - 2026-11-13
  - 2026-11-16
  - 2026-11-17
  - 2026-11-18
  - 2026-11-19
  - 2026-11-20
  - 2026-11-23
  - 2026-11-24

The extension path (`research/extend_paper_trading_state.py`, Cycle 854
contract) never writes `data/raw`; it fetches into a scratch directory that is
discarded. Sessions listed above therefore rest only on the state file itself.

### Provider digests

Sessions extended after this audit was introduced also write a
`provider_digest_YYYYMMDD.json` next to the paper-trading artifacts. It records
the canonical sha256 of the exact market slice handed to the update plus the
last two sessions' closes per universe symbol. A digest is an *attestation of
the provider inputs*, not a substitute for committed raw data: it does not make
a session re-derivable, but it can be compared against a later governed
`data/raw` refresh or a provider re-fetch.

Digest-attested unverified sessions:   - 2026-11-19
  - 2026-11-20
  - 2026-11-23
  - 2026-11-24

This cycle's extension: no session extended (digest requirement not triggered)

Digests are validated for schema, session/universe consistency and positive,
finite closes; a malformed digest fails the audit (exit 1) rather than being
silently ignored.

## Metric recurrence and decision sensitivity

| quantity | value |
|---|---|
| stored `rolling_sharpe_63d` | `-2.1090291833779418` |
| reproduced from stored returns (last 63) | `-2.1090291833779418` |
| reproduced exactly | `True` |
| covered-only `rolling_sharpe_63d` (through `2026-11-10`) | `-1.4394168982987599` |
| alert threshold | `0.5` |
| `low_rolling_sharpe` under full window | `True` |
| `low_rolling_sharpe` under covered-only window | `True` |

Interpretation: the `low_rolling_sharpe` verdict is **unchanged** under the covered-only window.

## Reproduce

```
python research/paper_record_raw_coverage_audit.py
```
