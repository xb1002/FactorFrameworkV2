# factor_library/service.py
from pathlib import Path
from typing import Dict, Iterable, Optional, List
import pandas as pd

from factor_engine.engine import FactorEngine
from evaluation.engine import EvaluatorEngine, EvalResult

from .interfaces import FactorEntry
from .storage import FactorStore
from .admission import AdmissionRule

from factor_engine.registry import FactorSpec  # 直接复用你已有的

class FactorLibrary:
    """
    对外暴露的“因子库”服务，负责：
    - 手动入库
    - 自动入库
    - 对外提供：
        1) 因子计算接口
        2) 因子评价接口（获取 EvalResult）
    """
    def __init__(
        self,
        manual_store: FactorStore,
        auto_store: FactorStore,
        factor_engine: FactorEngine,
        evaluator_engine: EvaluatorEngine,
        admission_rule: Optional[AdmissionRule] = None,
    ):
        self.manual_store = manual_store
        self.auto_store = auto_store
        self.factor_engine = factor_engine
        self.evaluator_engine = evaluator_engine
        self.admission_rule = admission_rule

    # 1) 手动入库：只要给出 FactorSpec + 一些元信息，就入库
    def manual_admit(
        self,
        spec: FactorSpec,
        description: str = "",
        tags: Optional[List[str]] = None,
        eval_result: Optional[EvalResult] = None,
    ) -> None:
        """
        手动入库：不检查评价结果，直接记为 'manual' 因子。
        """
        entry = FactorEntry(
            spec=spec,
            source_type="manual",
            description=description,
            tags=tags or [],
            last_eval_metrics=eval_result.metrics if eval_result else {},
        )
        self.manual_store.save_entry(entry)

    # 2) 自动入库：评价达标则放入 auto 仓库
    def auto_admit_from_eval(
        self,
        spec: FactorSpec,
        eval_result: EvalResult,
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> bool:
        """
        自动入库：根据 admission_rule 和 EvalResult.metrics 决定是否入库。
        返回是否入库成功。
        """
        if self.admission_rule is None:
            # 没有配置规则就不做自动入库
            return False
        
        metrics = eval_result.metrics
        if not self.admission_rule.is_pass(metrics):
            return False
        
        entry = FactorEntry(
            spec=spec,
            source_type="auto",
            description=description,
            tags=tags or [],
            last_eval_metrics=metrics,
        )
        self.auto_store.save_entry(entry)
        return True

    # 3) 对外接口：因子计算
    def compute_factor(
        self,
        df: pd.DataFrame,
        name: str,
        version: Optional[str] = None,
        **params,
    ) -> pd.Series:
        """
        对外统一的因子计算入口。
        - 先从 manual_store 查找
        - 查不到再从 auto_store 查找
        - 找到对应 FactorSpec 后，交给 FactorEngine 计算
        """
        entry = (
            self.manual_store.load_entry(name, version)
            or self.auto_store.load_entry(name, version)
        )
        if entry is None:
            raise ValueError(f"Factor not found in library: {name} (version={version})")
        
        # 关键设计点：
        #   计算因子时，依然使用 FactorEngine（保持你现有生态）
        #   这里不自己调用 spec.func，避免重复逻辑
        return self.factor_engine.compute_one(
            df=df,
            factor=entry.spec,   # 传递 FactorSpec 对象
            **params,
        )
    
    def get_factor_spec(
        self,
        name: str,
        version: Optional[str] = None,
    ) -> Optional[FactorSpec]:
        """
        获取因子规格（FactorSpec）
        - 先从 manual_store 查找
        - 查不到再从 auto_store 查找
        """
        entry = (
            self.manual_store.load_entry(name, version)
            or self.auto_store.load_entry(name, version)
        )
        if entry is None:
            return None
        return entry.spec
    
    def get_factor_entry(
        self,
        name: str,
        version: Optional[str] = None,
    ) -> Optional[FactorEntry]:
        """
        获取因子条目（FactorEntry）
        - 先从 manual_store 查找
        - 查不到再从 auto_store 查找
        """
        entry = (
            self.manual_store.load_entry(name, version)
            or self.auto_store.load_entry(name, version)
        )
        return entry
    
    def list_all_factors(
        self,
        source_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[FactorEntry]:
        """
        列出所有因子
        
        Args:
            source_type: 筛选来源类型，None 表示全部，'manual' 或 'auto'
            tags: 筛选标签，None 表示全部，否则返回包含任一标签的因子
            
        Returns:
            因子条目列表
        """
        entries = []
        
        # 从 manual_store 获取
        if source_type is None or source_type == "manual":
            entries.extend(self.manual_store.list_entries())
        
        # 从 auto_store 获取
        if source_type is None or source_type == "auto":
            entries.extend(self.auto_store.list_entries())
        
        # 按标签筛选
        if tags is not None:
            entries = [
                entry for entry in entries
                if any(tag in entry.tags for tag in tags)
            ]
        
        return entries
    
    def list_factor_names(
        self,
        source_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[str]:
        """
        列出所有因子名称
        
        Args:
            source_type: 筛选来源类型
            tags: 筛选标签
            
        Returns:
            因子名称列表（格式：name_version）
        """
        entries = self.list_all_factors(source_type=source_type, tags=tags)
        return [f"{entry.spec.name}_{entry.spec.version}" for entry in entries]
    
    def search_factors(
        self,
        keyword: Optional[str] = None,
        source_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[FactorEntry]:
        """
        搜索因子
        
        Args:
            keyword: 搜索关键词（匹配名称或描述）
            source_type: 筛选来源类型
            tags: 筛选标签
            
        Returns:
            符合条件的因子条目列表
        """
        entries = self.list_all_factors(source_type=source_type, tags=tags)
        
        # 按关键词筛选
        if keyword is not None:
            keyword_lower = keyword.lower()
            entries = [
                entry for entry in entries
                if keyword_lower in entry.spec.name.lower()
                or keyword_lower in entry.description.lower()
            ]
        
        return entries
    
    def get_factor_count(self, source_type: Optional[str] = None) -> Dict[str, int]:
        """
        获取因子数量统计
        
        Args:
            source_type: 筛选来源类型，None 表示统计所有
            
        Returns:
            统计字典，如 {"manual": 10, "auto": 5, "total": 15}
        """
        if source_type is None:
            manual_count = len(self.manual_store.list_entries())
            auto_count = len(self.auto_store.list_entries())
            return {
                "manual": manual_count,
                "auto": auto_count,
                "total": manual_count + auto_count,
            }
        elif source_type == "manual":
            count = len(self.manual_store.list_entries())
            return {"manual": count}
        elif source_type == "auto":
            count = len(self.auto_store.list_entries())
            return {"auto": count}
        else:
            raise ValueError(f"Invalid source_type: {source_type}")

    # 4) 对外接口：获取因子评价报告
    def get_factor_report(
        self,
        df: pd.DataFrame,
        name: str,
        horizons: Iterable[int],
        evaluator_name: str = "common_eval",
        version: Optional[str] = None,
    ) -> Dict[int, EvalResult]:
        """
        对外统一的“因子评价报告”入口：
        - 内部先通过因子库算出该因子（compute_factor）
        - 再调用 EvaluatorEngine 评价，得到 {horizon: EvalResult}
        """
        factor = self.compute_factor(df=df, name=name, version=version)
        
        reports = self.evaluator_engine.evaluate_multi_horizons(
            df=df,
            factor=factor,
            horizons=list(horizons),
            evaluator=evaluator_name,
        )
        return reports
