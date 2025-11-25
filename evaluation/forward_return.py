# evaluation/forward_return.py
from __future__ import annotations
from typing import List, Dict, Optional
import pandas as pd
import numpy as np

def build_forward_returns(
    df: pd.DataFrame,
    horizons: List[int],
    price_col: str = "close",
    kind: str = "simple",
) -> pd.DataFrame:
    """
    生成未来收益表 ret_fwd_{h}d

    df:
      MultiIndex(date, code) 的 DataFrame，至少包含 price_col
    horizons:
      [1,5,10,...]
    price_col:
      用哪个价格算未来收益（A股建议用复权 close）
    kind:
      simple:  (P_{t+h}/P_t - 1)
      log:     log(P_{t+h}/P_t)

    return:
      DataFrame(index=df.index, columns=[ret_fwd_1d, ret_fwd_5d, ...])
    """
    if price_col not in df.columns:
        raise ValueError(f"price_col '{price_col}' not in df.columns")

    px = df[price_col]
    # 按 code 做时间序列 shift，取未来价格
    g = px.groupby(level="code")

    out: Dict[str, pd.Series] = {}
    for h in horizons:
        future_px = g.shift(-h)
        if kind == "simple":
            ret = future_px / px - 1.0
        elif kind == "log":
            ret = np.log(future_px / px)
        else:
            raise ValueError("kind must be 'simple' or 'log'")

        out[f"ret_fwd_{h}d"] = ret

    return pd.DataFrame(out)
