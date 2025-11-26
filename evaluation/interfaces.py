# evaluation/interfaces.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Sequence, Union, TypeAlias
from abc import ABC, abstractmethod
import pandas as pd


# =========================
# 1) 统一输出结果基类（dataclass OK）
# =========================
@dataclass
class EvalResult:
    """
    evaluator 的统一输出基类
    
    evaluator_name: 评价器名
    factor_name: 因子名（可选）
    metrics: 数值指标
    artifacts: 绘图/后处理用的结构化数据（Series/DataFrame/ndarray）
    notes: 其他备注信息
    
    Note:
        子类应该继承此类并实现 plot_artifacts 方法来提供特定的绘图功能
    """
    evaluator_name: str
    factor_name: Optional[str] = None

    metrics: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    notes: Dict[str, Any] = field(default_factory=dict)

    # 添加 horizon 字段
    horizon: int = 1

    def plot_artifacts(
        self,
        show_fig: bool = False,
        figsize: Optional[tuple] = None,
        dpi: int = 100,
        style: str = "default",
        save_path: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        绘制 artifacts 中的图表
        
        Args:
            show_fig: 是否显示图表（默认False）
                - True: 自动显示所有图表，适合完整报告
                - False: 返回Figure对象但不显示，适合选择性查看
            figsize: 图表尺寸 (width, height)，None则使用各图表默认尺寸
            dpi: 图表分辨率，默认100
            style: matplotlib样式，如 'default', 'seaborn', 'ggplot' 等
            save_path: 保存路径，如果指定则保存所有图表到该目录
            **kwargs: 子类特定的绘图参数
        
        Returns:
            Dict[str, Any]: 包含各个图表对象的字典
            {
                "figure_name": matplotlib.figure.Figure,
                ...
            }
        
        Note:
            - 默认返回空字典，子类应该根据自己的 artifacts 实现具体的绘图逻辑
            - 子类可以通过 **kwargs 接收特定参数（如 horizon, show_labels 等）
        
        Examples:
            # 方式1: 不显示，返回Figure对象供选择
            figs = result.plot_artifacts(close_figures=True)
            figs["rank_ic_series"]  # 只显示这一个
            
            # 方式2: 显示所有图表
            result.plot_artifacts(close_figures=False)
            
            # 方式3: 保存所有图表
            result.plot_artifacts(save_path="./output/plots")
            
            # 方式4: 自定义样式和尺寸
            result.plot_artifacts(
                figsize=(14, 6),
                dpi=150,
                style='seaborn',
                close_figures=False
            )
        """
        raise NotImplementedError(
            "base EvalResult does not implement plot_artifacts. "
        )

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
