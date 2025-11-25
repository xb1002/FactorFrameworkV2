# factor_library/interfaces.py
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional
from factor_engine.registry import FactorSpec  # 直接复用你已有的

SourceType = Literal["manual", "auto"]

@dataclass
class FactorEntry:
    """
    因子库中的一条记录（不算因子，只是描述和管理信息）
    """
    spec: FactorSpec                  # 关联的因子定义（含 func）
    source_type: SourceType           # 'manual' 或 'auto'
    tags: List[str] = field(default_factory=list)      # 分类标签（可选）
    description: str = ""                             # 因子说明
    last_eval_metrics: Dict[str, float] = field(default_factory=dict)  # 最近一次评价指标（可选）
