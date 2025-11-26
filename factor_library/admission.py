# factor_library/admission.py
from dataclasses import dataclass
from typing import Dict
from evaluation.interfaces import EvalResult  # 你的 EvalResult

@dataclass
class AdmissionRule:
    """
    自动入库的阈值规则
    （你可以先只用一套规则，未来需要多套再扩展）
    """
    min_rank_ic: float = 0.02
    min_rank_ic_ir: float = 0.4
    max_top_turnover_20_mean: float = 0.6
    min_monotonic_mean: float = 0.1
    
    def is_pass(self, metrics: Dict[str, float], horizon: int) -> bool:
        """
        给一份 metrics（来自 EvalResult.metrics），判断是否满足入库标准
        """
        rank_ic_mean = metrics.get("rank_ic_mean", 0.0)
        rank_ic_ir = metrics.get("rank_ic_ir", 0.0)
        top_turnover_20_mean = metrics.get("top_turnover_20_mean", 1.0)
        monotonic_mean = metrics.get("monotonic_mean", 0.0)

        passed = (
            abs(rank_ic_mean) >= self.min_rank_ic and
            abs(rank_ic_ir) >= self.min_rank_ic_ir and
            (top_turnover_20_mean / horizon) <= self.max_top_turnover_20_mean and
            abs(monotonic_mean) >= self.min_monotonic_mean
        )

        return passed