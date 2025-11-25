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

    def evaluate_one(
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

    def evaluate_all(
        self,
        factor: pd.Series,
        ret: pd.Series,
        evaluators: EvaluatorList = None,
        per_evaluator_params: PerEvaluatorParams = None,
        **override_params: Any,
    ) -> Dict[str, EvalResult]:
        """评价单个因子，使用多个评价器
        Args:
            factor: 因子值序列
            ret: 收益率序列
            evaluators: 评价器列表，若为 None 则使用所有注册的评价器
            per_evaluator_params: 每个评价器的特定参数覆盖
            override_params: 所有评价器通用的参数覆盖
        Returns:
            Dict[str, EvalResult]: 评价结果字典，键为评价器名称
        """
        tmp = self.align(factor, ret)
        evs = list(list_evaluators()) if evaluators is None else [
            get_evaluator(e) if isinstance(e, str) else e for e in evaluators
        ]

        out: Dict[str, EvalResult] = {}
        for ev in evs:
            params = dict(ev.default_params)

            if per_evaluator_params and ev.name in per_evaluator_params:
                params.update(per_evaluator_params[ev.name])

            params.update(override_params)

            res = ev.evaluate(tmp["factor"], tmp["ret"], **params)
            if res.factor_name is None:
                res.factor_name = factor.name # type: ignore

            out[ev.name] = res

        return out
    
    def evaluate_factors(
        self,
        df: pd.Series | pd.DataFrame,  # 基础数据表，需包含价格列
        factor_df: pd.Series | pd.DataFrame,  # 单个或多个因子值表
        horizons: List[int],
        price_col: str = "close",
        kind: Literal["simple", "log"] = "simple",
        evaluators: EvaluatorList = None,
        per_evaluator_params: PerEvaluatorParams = None,
    ) -> Dict[str, Dict[int, Dict[str, EvalResult]]]:
        """
        多因子 + 多 horizon 批量评价
        Args:
            df: 基础数据表，需包含价格列
            factor_df: 因子值 DataFrame，列为不同因子
            horizons: 评价的收益率 horizon 列表
            price_col: 用于计算收益率的价格列名
            kind: 收益率计算方式，simple 或 log
            evaluators: 评价器列表，若为 None 则使用所有注册的评价器
            per_evaluator_params: 每个评价器的特定参数覆盖
        Returns:
            {factor_name: {horizon: {evaluator_name: EvalResult}}}
        """
        # 确保 df， factor_df 为 DataFrame
        if isinstance(factor_df, pd.Series):
            factor_df = factor_df.to_frame(name=factor_df.name or "factor")
        if isinstance(df, pd.Series):
            df = df.to_frame(name=df.name or price_col)
        
        # 1) 生成 forward returns
        ret_df = build_forward_returns(df, horizons, price_col=price_col, kind=kind)

        results = {}
        for fname in factor_df.columns:
            f = factor_df[fname]
            results[fname] = {}
            for h in horizons:
                r = ret_df[f"ret_fwd_{h}d"]
                results[fname][h] = self.evaluate_all(
                    f, r,
                    evaluators=evaluators,
                    per_evaluator_params=per_evaluator_params,
                )
        return results
    
    def list_evaluators(self) -> List[str]:
        """列出所有注册的评价器名称"""
        return [ev.name for ev in list_evaluators()]
