def run_baseline(close):
    print("\n=== [1] Baseline Backtest (252, 21, 0.5) ===")
    res = eval_config(close, *BASELINE)
    net_ret = res["net_ret"]
    weights = res["weights"]

    test_mask = net_ret.index >= pd.Timestamp(TEST_START, tz="UTC")
    test_ret = net_ret[test_mask]
    test_w = weights[test_mask]

    daily_ret = close.pct_change().fillna(0.0)
    port_ret = (weights * daily_ret).sum(axis=1)
    wc = weights.diff().abs().sum(axis=1)
    costs = wc * TOTAL_COST
    gross_ret = port_ret
    exposure = weights.abs().sum(axis=1)
    n_long = (weights > 0).sum(axis=1)
    turnover = wc

    sim_df = pd.DataFrame({
        "net_return": net_ret, "gross_return": gross_ret,
        "cost": costs, "turnover": turnover, "exposure": exposure, "n_long": n_long,
    })
    for col in close.columns:
        sim_df[f"weight_{col}"] = weights[col]

    SIM_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    sim_df.to_parquet(SIM_PARQUET)
    print(f"  Daily series -> {SIM_PARQUET} ({len(sim_df):,} rows)")

    wchanges = weights.diff().abs()
    trade_rows = []
    for date, row in wchanges.iterrows():
        changed = row[row > 1e-10]
        if len(changed) == 0:
            continue
        for sym, ch in changed.items():
            direction = "buy" if weights.loc[date, sym] > 0 else "sell"
            trade_rows.append({
                "date": date, "symbol": sym, "side": direction,
                "weight_change": ch, "cost": ch * TOTAL_COST,
                "weight_after": weights.loc[date, sym],
            })
    trades_df = pd.DataFrame(trade_rows)
    trades_df.to_parquet(TRADES_PARQUET)
    print(f"  Trade log -> {TRADES_PARQUET} ({len(trades_df):,} trades)")

    weights.to_parquet(WEIGHTS_PARQUET)
    print(f"  Weights -> {WEIGHTS_PARQUET} ({len(weights):,} rows)")

    test_metrics = compute_metrics(test_ret, test_w, COMMISSION_BPS, SLIPPAGE_BPS, RF_ANNUAL)
    return {
        "res": res, "net_ret": net_ret, "weights": weights,
        "test_ret": test_ret, "test_w": test_w, "test_metrics": test_metrics,
        "sim_df": sim_df, "trades_df": trades_df,
    }


def run_walkforward(close):
    print("\n=== [2] Walk-Forward Evaluation (48 folds, fixed params) ===")
    splits = generate_walkforward_splits(
        START_DATE, END_DATE, WF_TRAIN_YEARS, WF_TEST_MONTHS, WF_STEP_MONTHS,
        WF_PURGE_DAYS, WF_EMBARGO_DAYS,
    )
    print(f"  Folds: {len(splits)}")

    def config_fn(symbols, start, end):
        return eval_config_period(close, *BASELINE, start, end)

    rows = []
    for i, sp in enumerate(splits):
        print(f"  Fold {i+1}/{len(splits)}: train {sp['train_start']}->{sp['train_end']}, "
              f"test {sp['test_start']}->{sp['test_end']}")
        try:
            train_ret, train_w = config_fn(UNIVERSE, sp["train_start"], sp["train_end"])
            test_ret, test_w = config_fn(UNIVERSE, sp["test_start"], sp["test_end"])
            train_m = compute_metrics(train_ret, train_w, COMMISSION_BPS, SLIPPAGE_BPS, RF_ANNUAL)
            test_m = compute_metrics(test_ret, test_w, COMMISSION_BPS, SLIPPAGE_BPS, RF_ANNUAL)
            rows.append({
                "fold": i + 1,
                "train_start": sp["train_start"], "train_end": sp["train_end"],
                "test_start": sp["test_start"], "test_end": sp["test_end"],
                "train_sharpe": train_m.get("sharpe_ratio", np.nan),
                "train_ann_return": train_m.get("annualized_return", np.nan),
                "test_sharpe": test_m.get("sharpe_ratio", np.nan),
                "test_ann_return": test_m.get("annualized_return", np.nan),
                "test_max_dd": test_m.get("max_drawdown", np.nan),
                "test_turnover": test_m.get("annualized_turnover", np.nan),
                "test_trades": test_m.get("trade_count", np.nan),
                "test_profit_factor": test_m.get("profit_factor", np.nan),
                "test_sortino": test_m.get("sortino_ratio", np.nan),
            })
        except Exception as exc:
            print(f"    ERROR: {exc}")
            rows.append({
                "fold": i + 1,
                "train_start": sp["train_start"], "train_end": sp["train_end"],
                "test_start": sp["test_start"], "test_end": sp["test_end"],
                "train_sharpe": np.nan, "train_ann_return": np.nan,
                "test_sharpe": np.nan, "test_ann_return": np.nan,
                "test_max_dd": np.nan, "test_turnover": np.nan,
                "test_trades": np.nan, "test_profit_factor": np.nan, "test_sortino": np.nan,
            })

    wf_df = pd.DataFrame(rows)
    summary = summarize_walkforward(wf_df)
    print(f"  Mean OOS Sharpe: {summary.get('mean_test_sharpe', np.nan):.4f}")
    print(f"  % Positive folds: {summary.get('pct_positive_sharpe', np.nan):.1%}")
    print(f"  Pooled OOS trades: {summary.get('total_test_trades', 0)}")
    return {"wf_df": wf_df, "summary": summary}