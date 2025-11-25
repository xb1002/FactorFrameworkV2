# factor_library/service.py
from pathlib import Path
from typing import Dict, Iterable, Optional
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
        tags: Optional[list[str]] = None,
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
        tags: Optional[list[str]] = None,
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
            factor_name=entry.spec,   # 与 registry 中一致
            **params,
        )

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
