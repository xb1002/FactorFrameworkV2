# factor_library/__init__.py
"""
因子库组件 - 统一对外接口

主要组件：
- FactorLibrary: 因子库服务类，提供手动入库、自动入库、因子计算、因子评价等功能
- FactorStore: 因子存储类，负责因子的持久化
- FactorEntry: 因子库条目数据类
- AdmissionRule: 自动入库规则类
"""

from .interfaces import FactorEntry, SourceType
from .storage import FactorStore
from .admission import AdmissionRule
from .service import FactorLibrary

__all__ = [
    "FactorEntry",
    "SourceType",
    "FactorStore",
    "AdmissionRule",
    "FactorLibrary",
]
