# evaluation/interfaces.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Sequence, Union, TypeAlias
from abc import ABC, abstractmethod
import pandas as pd


# =========================
# 1) 统一输出结果（dataclass OK）
# =========================
@dataclass
class EvalResult:
    """
    evaluator 的统一输出
    evaluator_name: 评价器名
    factor_name: 因子名（可选）
    metrics: 数值指标
    artifacts: 绘图/后处理用的结构化数据（Series/DataFrame/ndarray）
    notes: 其他备注信息
    """
    evaluator_name: str
    factor_name: Optional[str] = None

    metrics: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    notes: Dict[str, Any] = field(default_factory=dict)


# =========================
# 2) IEvaluator 抽象接口（非 dataclass）
# =========================
class IEvaluator(ABC):
    """
    评价器接口（策略）
    子类只需要实现 evaluate
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """评价器名（registry 的 key）"""

    @property
    def default_params(self) -> Dict[str, Any]:
        """默认参数（可选）"""
        return {}

    @abstractmethod
    def evaluate(
        self,
        factor: pd.Series,
        ret: pd.Series,
        **params: Any,
    ) -> EvalResult:
        """
        输入:
          factor: MultiIndex(date, code)
          ret:    MultiIndex(date, code)
        输出:
          EvalResult
        """


# =========================
# 3) Engine 用的类型别名
# =========================
EvaluatorLike: TypeAlias = Union[str, IEvaluator]
EvaluatorList: TypeAlias = Optional[Sequence[EvaluatorLike]]

PerEvaluatorParams: TypeAlias = Optional[Dict[str, Dict[str, Any]]]
"""
每个 evaluator 独立覆盖参数:
{
  "rank_ic": {"rolling_window": 252},
  "decile": {"q": 10}
}
"""
