# Next Agent Task: Survey Free Data Sources for Point-in-Time Microcap Market Cap

## Context

The paper-trading monitoring loop is stuck: the session timestamp (2026-10-15T00:41:21Z) is before US market close (~20:00 UTC), so 2026-10-15 data cannot yet be fetched. Cycles 45–62 have repeatedly confirmed no new trading days available. All primary go/no-go gates pass (track record 447 days, Sharpe 1.93, max DD -2.93%, 6 regime flips). The `low_rolling_sharpe` drift flag persists at 3 consecutive days, below the >20-day threshold for strategy review.

**Higher-value task:** The microcap mom121 cross-sectional momentum hypothesis (`research/hypotheses/mom121_microcap_001.md`) is **Blocked by data** — no point-in-time microcap universe can be constructed because the repository caches only ETF OHLCV data (19 files) and yfinance does not provide historical market cap, shares outstanding, or delisting events (`research/experiments/mom121_microcap_001.md`, Section A). The README explicitly documents the next step as: "survey free data sources and run a clearly-labelled exploratory diagnostic."

## Objective

Survey freely accessible data sources to determine which can provide point-in-time market capitalization (or shares outstanding) for individual US stocks — the missing field that blocks the microcap data gate. Document findings with evidence. If any source can provide sufficient data for a clearly-labelled exploratory diagnostic, run that diagnostic with full disclosure of survivorship and look-ahead limitations. Do not add new dependencies or make infrastructure changes without documented necessity.

## Acceptance Criteria

1. **Survey free/low-cost data sources** accessible from this environment (no paid subscriptions or credentials). Investigate at minimum:
   - yfinance enhanced API (e.g., `Ticker.history` with `actions=True`, `Ticker.funds` if crypto — not applicable here; check for any market-cap endpoint)
   - Polygon.io (free tier) — check if `/vX/reference/tickers` or similar provides historical shares/market cap
   - Alpha Vantage (free tier) — check `OVERVIEW` or `TIME_SERIES` for market cap fields
   - IEX Cloud (free tier) — check `stats` or `book` endpoints for market cap
   - SEC EDGAR bulk data (free) — check if form 10-K/10-Q filings contain historical shares outstanding
   - FRED — check for any market cap or share count series
   - Any other free source mentioned in the repository or discoverable

2. **For each candidate source, document:**
   - Whether historical (point-in-time) market cap or shares outstanding is available
   - Whether delisting data is available
   - Whether point-in-time universe screening (by market cap) is possible
   - API access requirements (free tier, rate limits, credentials needed)
   - Evidence: actual API response samples or documented capability (not claims)

3. **Do NOT:**
   - Add new dependencies to `requirements.txt` without documented necessity
   - Create paid accounts or use credentials
   - Make infrastructure changes
   - Run a confirmatory microcap backtest (data gate blocks this)
   - Claim an edge exists based on imperfect data

4. **If a viable free source is found** (provides point-in-time market cap ≥ 2 years of history for a sample of tickers):
   - Run a clearly-labelled exploratory diagnostic: fetch current-ticker microcap basket, compute 12-1 momentum ranks, document all limitations (survivorship bias, look-ahead bias, stale prices, no delisting, no point-in-time universe)
   - Label result as **exploratory only** — must not be promoted as a valid microcap backtest

5. **Write findings** to `research/experiments/mom121_datagate_survey.md`

6. **Run tests**: `python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v`

## Validation Commands

```bash
# Check existing yfinance capabilities (no historical market cap)
python3 -c "
import yfinance as yf
t = yf.Ticker('SIRI')
print('Has get_market_cap_history:', hasattr(t, 'get_market_cap_history'))
i = t.info
print('marketCap (current snapshot):', i.get('marketCap'))
print('sharesOutstanding (current snapshot):', i.get('sharesOutstanding'))
"

# Survey free data sources
python3 -c "
import yfinance as yf
# Check if YFinanceFetcher supports market cap
d = yf.download('SPY', period='1mo', progress=False)
print('download columns:', list(d.columns))
"

# Check if polygon/alpaca/iex are installed
python3 -c "import polygon; print('polygon', polygon.__version__)" 2>&1 || echo "polygon not installed"
python3 -c "import alpaca_trade_api; print('alpaca installed')" 2>&1 || echo "alpaca not installed"
python3 -c "import iexfinance; print('iexfinance installed')" 2>&1 || echo "iexfinance not installed"
python3 -c "import alpha_vantage; print('alpha_vantage installed')" 2>&1 || echo "alpha_vantage not installed"

# Check SEC EDGAR access
python3 -c "
import urllib.request
url = 'https://data.sec.gov/submissions/CIK=0000093680.json'
req = urllib.request.Request(url, headers={'User-Agent': 'ResearchBot/1.0 (research@example.com)'})
try:
    resp = urllib.request.urlopen(req, timeout=10)
    print('SEC EDGAR accessible:', resp.status)
    import json
    data = json.loads(resp.read()[:200])
    print('Keys:', list(data.keys())[:5])
except Exception as e:
    print('SEC EDGAR error:', e)
"

# Run tests
python3 -m pytest .github/scripts/test_kilo_supervisor_loop.py -v
```

## Scope Boundaries

- **Research/survey only**: No live trading, no paid data, no new dependencies without documented necessity
- **No confirmatory backtest**: The data gate has failed; any diagnostic must be clearly labelled exploratory
- **Survey existing infrastructure first**: Check what's already configured in `config/settings.yaml` and `src/data/`
- **Document limitations**: Any imperfect data source must be documented with full disclosure of survivorship, look-ahead, and delisting bias
- **No live trading infrastructure**: Do not add scheduled jobs, brokerage APIs, or execution systems
- **Do not commit** unless explicitly requested
