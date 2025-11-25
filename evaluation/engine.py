# evaluation/engine.py
from __future__ import annotations

from typing import Any, Dict, List, Literal
import pandas as pd

from .interfaces import (
    IEvaluator, EvalResult, EvaluatorLike, EvaluatorList, PerEvaluatorParams
)
from .registry import get_evaluator, list_evaluators

from .forward_return import build_forward_returns


class EvaluatorEngine:
    def align(self, factor: pd.Series, ret: pd.Series) -> pd.DataFrame:
        """对齐因子和收益率，去除缺失值"""
        tmp = pd.DataFrame({"factor": factor, "ret": ret})
        return tmp.dropna()

    def _evaluate_one_horizon(
        self,
        factor: pd.Series,
        ret: pd.Series,
        evaluator: EvaluatorLike,
        **override_params: Any,
    ) -> EvalResult:
        """评价单个因子
        Args:
            factor: 因子值序列
            ret: 收益率序列
            evaluator: 评价器实例或名称
            override_params: 覆盖评价器默认参数的参数
        Returns:
            EvalResult: 评价结果
        """
        if isinstance(evaluator, str):
            evaluator = get_evaluator(evaluator)

        tmp = self.align(factor, ret)
        res = evaluator.evaluate(tmp["factor"], tmp["ret"], **override_params)

        # 自动补 factor_name（不改 evaluator 逻辑）
        if res.factor_name is None:
            res.factor_name = factor.name # type: ignore

        return res
    
    def evaluate_one_horizon(
        self,
        df: pd.DataFrame | pd.Series,  # 基础数据表，需包含价格列
        factor: pd.Series,  # 单个因子值序列
        horizon: int,
        evaluator: EvaluatorLike,
        price_col: str = "close",
        kind: Literal["simple", "log"] = "simple",
        **override_params: Any,
    ) -> EvalResult:
        """
        单因子 + 单 evaluator 评价
        Args:
            df: 基础数据表，需包含价格列
            factor: 单个因子值序列
            horizon: 评价的收益率 horizon
            price_col: 用于计算收益率的价格列名
            kind: 收益率计算方式，simple 或 log
            evaluator: 评价器实例或名称, 目前可选字符串有：'common_eval'
            override_params: 覆盖评价器默认参数的参数
        Returns:
            EvalResult: 评价结果
        """
        # 确保 df 为 DataFrame
        if isinstance(df, pd.Series):
            df = df.to_frame(name=df.name or price_col)
        
        # 1) 生成 forward returns
        ret_df = build_forward_returns(df, [horizon], price_col=price_col, kind=kind)
        ret = ret_df[f"ret_fwd_{horizon}d"]
        
        return self._evaluate_one_horizon(
            factor, ret,
            evaluator=evaluator,
            horizon=horizon,  # 传递 horizon
            **override_params,
        )
    
    def evaluate_multi_horizons(
        self,
        df: pd.DataFrame | pd.Series,  # 基础数据表，需包含价格列
        factor: pd.Series,  # 单个因子值序列
        horizons: List[int],  # 多个 horizon
        evaluator: EvaluatorLike,
        price_col: str = "close",
        kind: Literal["simple", "log"] = "simple",
        **override_params: Any,
    ) -> Dict[int, EvalResult]:
        """
        单因子 + 单 evaluator + 多 horizon
        Args:
            df: 基础数据表，需包含价格列
            factor: 单个因子值序列
            horizons: 评价的收益率 horizon 列表，例如 [1, 5, 10]
            evaluator: 评价器实例或名称, 目前可选字符串有：'common_eval'
            price_col: 用于计算收益率的价格列名
            kind: 收益率计算方式，simple 或 log
            override_params: 覆盖评价器默认参数的参数
        Returns:
            Dict[int, EvalResult]: {horizon: EvalResult}
        """
        # 确保 df 为 DataFrame
        if isinstance(df, pd.Series):
            df = df.to_frame(name=df.name or price_col)
        
        # 1) 生成所有 horizon 的 forward returns
        ret_df = build_forward_returns(df, horizons, price_col=price_col, kind=kind)

        out: Dict[int, EvalResult] = {}
        for horizon in horizons:
            ret = ret_df[f"ret_fwd_{horizon}d"]
            result = self._evaluate_one_horizon(
                factor, ret,
                evaluator=evaluator,
                horizon=horizon,
                **override_params,
            )
            out[horizon] = result
        
        return out
    
    @staticmethod
    def get_evaluator(name: str) -> IEvaluator:
        return get_evaluator(name)
    
    @staticmethod
    def list_evaluators() -> List[str]:
        """列出所有注册的评价器名称"""
        return [ev.name for ev in list_evaluators()]