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
    min_rank_ic: float = 0.03
    min_rank_ic_ir: float = 0.5
    min_group_ls_t: float = 2.0
    
    def is_pass(self, metrics: Dict[str, float]) -> bool:
        """
        给一份 metrics（来自 EvalResult.metrics），判断是否满足入库标准
        """
        return (
            metrics.get("rank_ic_mean", 0.0) >= self.min_rank_ic and
            metrics.get("rank_ic_ir", 0.0) >= self.min_rank_ic_ir and
            metrics.get("group_ls_t", 0.0) >= self.min_group_ls_t
        )
