"""
自动挖掘的因子（待评价入库）

所有在这里注册的因子会被 auto_batch.py 自动评价并判断是否入库
"""

import pandas as pd
import numpy as np
from factor_engine import register_factor


# 示例因子1：动量类
@register_factor(
    name="momentum_10d",
    required_fields=["close"],
    version="v1"
)
def momentum_10d(df: pd.DataFrame) -> pd.Series:
    """10日动量因子"""
    return df.groupby(level="code")["close"].pct_change(10)
