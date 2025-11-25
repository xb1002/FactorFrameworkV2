# factor_engine/engine.py
from __future__ import annotations

from typing import Any, Dict, List
import pandas as pd

from .interfaces import FactorSpec, FactorLike, FactorList, PerFactorParams
from .registry import get_factor, list_factors


class FactorEngine:
    """
    极简因子引擎：
    输入 df: MultiIndex(date, code)
    """

    def compute_one(
        self,
        df: pd.DataFrame,
        factor: FactorLike,
        **override_params: Any,
    ) -> pd.Series:
        """
        计算单因子

        override_params:
            本次调用对该因子 params 的覆盖（只作用于这个因子）
        """
        if not isinstance(df.index, pd.MultiIndex):
            raise TypeError("df index must be MultiIndex(date, code).")

        spec = get_factor(factor) if isinstance(factor, str) else factor

        missing = [f for f in spec.required_fields if f not in df.columns]
        if missing:
            raise ValueError(f"{spec.name} missing fields: {missing}")

        use_df = df[spec.required_fields] if spec.required_fields else df

        params = dict(spec.params)
        params.update(override_params)

        s = spec.func(use_df, **params)
        if not isinstance(s, pd.Series):
            raise TypeError(f"{spec.name} must return pd.Series.")

        if not s.index.equals(df.index):
            s = s.reindex(df.index)

        s.name = spec.name
        return s

    def compute_all(
        self,
        df: pd.DataFrame,
        factors: FactorList = None,
        per_factor_params: PerFactorParams = None,
        **override_params: Any,
    ) -> pd.DataFrame:
        """
        批量计算因子

        factors:
            None -> 计算 registry 中全部因子
            list[str|FactorSpec] -> 只计算指定因子

        per_factor_params:
            对“某些因子”做独立 params 覆盖（优先级高于全局 override）

        override_params:
            本次批量对所有因子的“全局覆盖参数”（优先级最低）
        """
        if not isinstance(df.index, pd.MultiIndex):
            raise TypeError("df index must be MultiIndex(date, code).")

        specs = list(list_factors()) if factors is None else list(factors)

        out: List[pd.Series] = []
        for f in specs:
            spec = get_factor(f) if isinstance(f, str) else f

            missing = [c for c in spec.required_fields if c not in df.columns]
            if missing:
                raise ValueError(f"{spec.name} missing fields: {missing}")

            use_df = df[spec.required_fields] if spec.required_fields else df

            params = dict(spec.params)

            # 1) per-factor 覆盖
            if per_factor_params and spec.name in per_factor_params:
                params.update(per_factor_params[spec.name])

            # 2) 全局覆盖
            params.update(override_params)

            s = spec.func(use_df, **params)
            if not isinstance(s, pd.Series):
                raise TypeError(f"{spec.name} must return pd.Series.")

            if not s.index.equals(df.index):
                s = s.reindex(df.index)

            s.name = spec.name
            out.append(s)

        return pd.concat(out, axis=1) if out else pd.DataFrame(index=df.index)
