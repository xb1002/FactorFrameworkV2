"""
自动挖掘的因子（待评价入库）

所有在这里注册的因子会被 auto_batch.py 自动评价并判断是否入库
"""

import pandas as pd
import numpy as np
from factor_engine import register_factor

# def factor_func(df: pd.DataFrame) -> pd.Series:
#     """
#     这里接受的是一个multi-index为(code, date)的DataFrame
#     需要返回一个与df索引对齐的Series
#     """
    
# 示例因子1：动量类
@register_factor(
    name="momentum_20d",
    required_fields=["close"],
    version="v1"
)
def momentum_20d(df: pd.DataFrame) -> pd.Series:
    """20日动量因子"""
    return df.groupby(level="code")["close"].pct_change(20)