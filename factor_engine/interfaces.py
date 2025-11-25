# factor_engine/interfaces.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Union, TypeAlias
import pandas as pd


# ---------------------------
# 1) 因子函数签名（接口）
# ---------------------------
FactorFunc: TypeAlias = Callable[..., pd.Series]
"""
所有因子函数都必须满足：
    func(df: pd.DataFrame, **params) -> pd.Series

- df 的 index 必须是 MultiIndex(date, code)
- 返回的 Series index 必须和 df.index 对齐（或可 reindex 对齐）
"""


# ---------------------------
# 2) 因子模型（接口）
# ---------------------------
@dataclass(frozen=True)
class FactorSpec:
    """
    极简因子规格（现在够用的那部分）

    name: 因子名（唯一 key）
    func: 因子函数 FactorFunc
    required_fields: 因子需要的字段（如 close/high/amount）
    params: 因子默认参数（window/lookback 等）
    version: 版本，便于复现与因子库管理
    """
    name: str
    func: FactorFunc
    required_fields: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    version: str = "v1"


# ---------------------------
# 3) 供 Engine 使用的类型别名（接口）
# ---------------------------
FactorLike: TypeAlias = Union[str, FactorSpec]
"""
引擎接受的因子形式：
- str：在 registry 里的因子名
- FactorSpec：手动构造的因子规格（扫参/临时因子）
"""

PerFactorParams: TypeAlias = Optional[Dict[str, Dict[str, Any]]]
"""
每因子独立的参数覆盖：
{
  "mom_20": {"window": 20},
  "vol_60": {"window": 60},
}
不传则表示不做 per-factor 覆盖
"""

FactorList: TypeAlias = Optional[Sequence[FactorLike]]
"""
compute_all 可传：
- None：计算 registry 全部因子
- Sequence[FactorLike]：只计算指定因子
"""
