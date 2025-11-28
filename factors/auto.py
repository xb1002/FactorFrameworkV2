"""Exploratory auto-generated factors for batch evaluation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from factor_engine import register_factor

WINDOWS = [1, 5, 20, 60]


def _rolling_op(series: pd.Series, window: int, method: str, **kwargs) -> pd.Series:
    return (
        series.groupby(level="code")
        .apply(lambda x: getattr(x.rolling(window), method)(**kwargs))
        .droplevel(0)
    )


def _rolling_corr(series: pd.Series, other: pd.Series, window: int) -> pd.Series:
    def corr_fn(group: pd.Series) -> pd.Series:
        matched = other.loc[group.index]
        return group.rolling(window).corr(matched)

    return series.groupby(level="code").apply(corr_fn).droplevel(0)


def _true_range(df: pd.DataFrame) -> pd.Series:
    grouped = df.groupby(level="code")
    prev_close = grouped["close"].shift(1)
    ranges = pd.concat(
        [
            grouped["high"] - grouped["low"],
            (grouped["high"] - prev_close).abs(),
            (grouped["low"] - prev_close).abs(),
        ],
        axis=1,
    )
    tr = ranges.max(axis=1)
    tr.index = df.index
    return tr


def _register_dynamic(name: str, required_fields: list[str]):
    def decorator(func):
        # Rename the function so pickling can locate it by module + name
        func.__name__ = name
        func.__qualname__ = name
        registered = register_factor(
            name=name, required_fields=required_fields, version="v1"
        )(func)
        globals()[name] = registered
        return registered

    return decorator


# Price momentum
for window in WINDOWS:
    @_register_dynamic(f"close_pct_change_{window}d", ["close"])
    def close_pct_change_factor(
        df: pd.DataFrame, window: int = window
    ) -> pd.Series:
        return df.groupby(level="code")["close"].pct_change(window)


# Log returns over different horizons
for window in WINDOWS:
    @_register_dynamic(f"log_return_{window}d", ["close"])
    def log_return_factor(df: pd.DataFrame, window: int = window) -> pd.Series:
        log_close = np.log(df["close"].replace(0, np.nan))
        return log_close.groupby(level="code").diff(window)


# Bias of close to simple moving average
for window in WINDOWS:
    @_register_dynamic(f"close_ma_bias_{window}d", ["close"])
    def close_ma_bias_factor(df: pd.DataFrame, window: int = window) -> pd.Series:
        close = df["close"]
        ma = _rolling_op(close, window, "mean")
        return close / ma - 1


# Bias of close to exponential moving average
for window in WINDOWS:
    @_register_dynamic(f"close_ema_bias_{window}d", ["close"])
    def close_ema_bias_factor(df: pd.DataFrame, window: int = window) -> pd.Series:
        close = df["close"]
        ema = (
            close.groupby(level="code")
            .apply(lambda x: x.ewm(span=window, adjust=False).mean())
            .droplevel(0)
        )
        return (close - ema) / ema


# Volatility of daily returns
for window in WINDOWS:
    @_register_dynamic(f"return_volatility_{window}d", ["close"])
    def return_volatility_factor(
        df: pd.DataFrame, window: int = window
    ) -> pd.Series:
        daily_ret = df.groupby(level="code")["close"].pct_change()
        return _rolling_op(daily_ret, window, "std")


# Volatility of intraday range
for window in WINDOWS:
    @_register_dynamic(f"range_volatility_{window}d", ["high", "low", "close"])
    def range_volatility_factor(
        df: pd.DataFrame, window: int = window
    ) -> pd.Series:
        range_ratio = (df["high"] - df["low"]) / df["close"].replace(0, np.nan)
        return _rolling_op(range_ratio, window, "std")


# Mean intraday range ratio
for window in WINDOWS:
    @_register_dynamic(f"range_mean_{window}d", ["high", "low", "close"])
    def range_mean_factor(df: pd.DataFrame, window: int = window) -> pd.Series:
        range_ratio = (df["high"] - df["low"]) / df["close"].replace(0, np.nan)
        return _rolling_op(range_ratio, window, "mean")


# Average distance of high to close
for window in WINDOWS:
    @_register_dynamic(f"high_close_spread_{window}d", ["high", "close"])
    def high_close_spread_factor(
        df: pd.DataFrame, window: int = window
    ) -> pd.Series:
        spread = (df["high"] - df["close"]) / df["close"].replace(0, np.nan)
        return _rolling_op(spread, window, "mean")


# Average distance of close to low
for window in WINDOWS:
    @_register_dynamic(f"low_close_spread_{window}d", ["low", "close"])
    def low_close_spread_factor(
        df: pd.DataFrame, window: int = window
    ) -> pd.Series:
        spread = (df["close"] - df["low"]) / df["close"].replace(0, np.nan)
        return _rolling_op(spread, window, "mean")


# Normalized average true range
for window in WINDOWS:
    @_register_dynamic(f"atr_normalized_{window}d", ["high", "low", "close"])
    def atr_normalized_factor(df: pd.DataFrame, window: int = window) -> pd.Series:
        norm_tr = _true_range(df) / df["close"].replace(0, np.nan)
        return _rolling_op(norm_tr, window, "mean")


# Volume momentum
for window in WINDOWS:
    @_register_dynamic(f"volume_momentum_{window}d", ["volume"])
    def volume_momentum_factor(
        df: pd.DataFrame, window: int = window
    ) -> pd.Series:
        return df.groupby(level="code")["volume"].pct_change(window)


# Volume z-score within window
for window in WINDOWS:
    @_register_dynamic(f"volume_zscore_{window}d", ["volume"])
    def volume_zscore_factor(df: pd.DataFrame, window: int = window) -> pd.Series:
        volume = df["volume"]
        mean = _rolling_op(volume, window, "mean")
        std = _rolling_op(volume, window, "std")
        return (volume - mean) / std.replace(0, np.nan)


# Amount momentum
for window in WINDOWS:
    @_register_dynamic(f"amount_momentum_{window}d", ["amount"])
    def amount_momentum_factor(
        df: pd.DataFrame, window: int = window
    ) -> pd.Series:
        return df.groupby(level="code")["amount"].pct_change(window)


# Mean float turnover by value
for window in WINDOWS:
    @_register_dynamic(
        f"turnover_float_mean_{window}d", ["amount", "market_cap_float"]
    )
    def turnover_float_mean_factor(
        df: pd.DataFrame, window: int = window
    ) -> pd.Series:
        turnover = df["amount"] / df["market_cap_float"].replace(0, np.nan)
        return _rolling_op(turnover, window, "mean")


# Mean total turnover by value
for window in WINDOWS:
    @_register_dynamic(
        f"turnover_total_mean_{window}d", ["amount", "market_cap_total"]
    )
    def turnover_total_mean_factor(
        df: pd.DataFrame, window: int = window
    ) -> pd.Series:
        turnover = df["amount"] / df["market_cap_total"].replace(0, np.nan)
        return _rolling_op(turnover, window, "mean")


# Money flow bias using intraday return and amount
for window in WINDOWS:
    @_register_dynamic(f"money_flow_balance_{window}d", ["open", "close", "amount"])
    def money_flow_balance_factor(
        df: pd.DataFrame, window: int = window
    ) -> pd.Series:
        intraday = (df["close"] - df["open"]) / df["open"].replace(0, np.nan)
        money_flow = intraday * df["amount"]
        return _rolling_op(money_flow, window, "sum")


# Correlation between return and volume change
for window in WINDOWS:
    @_register_dynamic(f"return_volume_corr_{window}d", ["close", "volume"])
    def return_volume_corr_factor(
        df: pd.DataFrame, window: int = window
    ) -> pd.Series:
        ret = df.groupby(level="code")["close"].pct_change()
        vol_chg = df.groupby(level="code")["volume"].pct_change()
        return _rolling_corr(ret, vol_chg, window)


# Mean absolute return
for window in WINDOWS:
    @_register_dynamic(f"abs_return_mean_{window}d", ["close"])
    def abs_return_mean_factor(
        df: pd.DataFrame, window: int = window
    ) -> pd.Series:
        ret = df.groupby(level="code")["close"].pct_change().abs()
        return _rolling_op(ret, window, "mean")


# Share of upside moves
for window in WINDOWS:
    @_register_dynamic(f"upside_return_share_{window}d", ["close"])
    def upside_return_share_factor(
        df: pd.DataFrame, window: int = window
    ) -> pd.Series:
        ret = df.groupby(level="code")["close"].pct_change()
        pos = ret.clip(lower=0)
        abs_ret = ret.abs()
        pos_sum = _rolling_op(pos, window, "sum")
        abs_sum = _rolling_op(abs_ret, window, "sum")
        return pos_sum / abs_sum.replace(0, np.nan)


# Share of downside moves
for window in WINDOWS:
    @_register_dynamic(f"downside_return_share_{window}d", ["close"])
    def downside_return_share_factor(
        df: pd.DataFrame, window: int = window
    ) -> pd.Series:
        ret = df.groupby(level="code")["close"].pct_change()
        neg = ret.clip(upper=0).abs()
        abs_ret = ret.abs()
        neg_sum = _rolling_op(neg, window, "sum")
        abs_sum = _rolling_op(abs_ret, window, "sum")
        return neg_sum / abs_sum.replace(0, np.nan)


# Rolling drawdown from local highs
for window in WINDOWS:
    @_register_dynamic(f"drawdown_{window}d", ["close"])
    def drawdown_factor(df: pd.DataFrame, window: int = window) -> pd.Series:
        close = df["close"]
        roll_max = _rolling_op(close, window, "max")
        return close / roll_max - 1


# Distance from local lows
for window in WINDOWS:
    @_register_dynamic(f"rebound_strength_{window}d", ["close"])
    def rebound_strength_factor(
        df: pd.DataFrame, window: int = window
    ) -> pd.Series:
        close = df["close"]
        roll_min = _rolling_op(close, window, "min")
        return close / roll_min - 1


# Mean open gap vs previous close
for window in WINDOWS:
    @_register_dynamic(f"gap_return_mean_{window}d", ["open", "close"])
    def gap_return_mean_factor(
        df: pd.DataFrame, window: int = window
    ) -> pd.Series:
        prev_close = df.groupby(level="code")["close"].shift(1)
        gap = (df["open"] - prev_close) / prev_close.replace(0, np.nan)
        return _rolling_op(gap, window, "mean")


# Gap volatility
for window in WINDOWS:
    @_register_dynamic(f"gap_volatility_{window}d", ["open", "close"])
    def gap_volatility_factor(
        df: pd.DataFrame, window: int = window
    ) -> pd.Series:
        prev_close = df.groupby(level="code")["close"].shift(1)
        gap = (df["open"] - prev_close) / prev_close.replace(0, np.nan)
        return _rolling_op(gap, window, "std")


# Frequency of limit-up events
for window in WINDOWS:
    @_register_dynamic(f"limit_up_rate_{window}d", ["limit_status"])
    def limit_up_rate_factor(
        df: pd.DataFrame, window: int = window
    ) -> pd.Series:
        limit_up = (df["limit_status"] == 1).astype(float)
        return _rolling_op(limit_up, window, "mean")


# Frequency of limit-down events
for window in WINDOWS:
    @_register_dynamic(f"limit_down_rate_{window}d", ["limit_status"])
    def limit_down_rate_factor(
        df: pd.DataFrame, window: int = window
    ) -> pd.Series:
        limit_down = (df["limit_status"] == -1).astype(float)
        return _rolling_op(limit_down, window, "mean")


# Return-weighted limit behavior
for window in WINDOWS:
    @_register_dynamic(
        f"limit_return_impact_{window}d", ["close", "limit_status"]
    )
    def limit_return_impact_factor(
        df: pd.DataFrame, window: int = window
    ) -> pd.Series:
        ret = df.groupby(level="code")["close"].pct_change()
        weighted = ret * df["limit_status"]
        return _rolling_op(weighted, window, "sum")


# Upper shadow proportion
for window in WINDOWS:
    @_register_dynamic(f"upper_shadow_mean_{window}d", ["open", "high", "close"])
    def upper_shadow_mean_factor(
        df: pd.DataFrame, window: int = window
    ) -> pd.Series:
        body_high = df[["open", "close"]].max(axis=1)
        upper_shadow = (df["high"] - body_high) / df["close"].replace(0, np.nan)
        return _rolling_op(upper_shadow, window, "mean")


# Lower shadow proportion
for window in WINDOWS:
    @_register_dynamic(f"lower_shadow_mean_{window}d", ["open", "low", "close"])
    def lower_shadow_mean_factor(
        df: pd.DataFrame, window: int = window
    ) -> pd.Series:
        body_low = df[["open", "close"]].min(axis=1)
        lower_shadow = (body_low - df["low"]) / df["close"].replace(0, np.nan)
        return _rolling_op(lower_shadow, window, "mean")


# Body-to-range ratio
for window in WINDOWS:
    @_register_dynamic(
        f"body_range_ratio_mean_{window}d", ["open", "high", "low", "close"]
    )
    def body_range_ratio_mean_factor(
        df: pd.DataFrame, window: int = window
    ) -> pd.Series:
        body = (df["close"] - df["open"]).abs()
        range_span = (df["high"] - df["low"]).replace(0, np.nan)
        ratio = body / range_span
        return _rolling_op(ratio, window, "mean")
