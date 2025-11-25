"""
手动挖到的因子复制粘贴到这里以确保pickle化存储时不会出错
"""

import pandas as pd
import numpy as np

from factor_engine import register_factor

@register_factor(
    name="liquidity_momentum_deviation",
    required_fields=["open", "close", "amount"],
    force_update=True,
)
def liquidity_momentum_deviation_factor(df: pd.DataFrame) -> pd.Series:
    def cal(g) -> pd.Series:
        mean = ((np.log(g["close"] / g["open"])) * g["amount"]).median()
        up_power =  ((np.log(g["close"] / g["open"])) * g["amount"] - mean) ** 2
        return up_power
    
    factor = df.groupby("date").apply(cal)
    factor.index = factor.index.droplevel(0)
    return factor