# evaluation/builtins.py
from __future__ import annotations

import pandas as pd
import numpy as np
import scipy.stats as st

from .interfaces import IEvaluator, EvalResult
from .registry import add_evaluator


class CommonFactorEvaluator(IEvaluator):
    """
    通用因子评价器（单 horizon）

    计算：
      - IC / Rank IC / Rank ICIR
      - top 20% 换手（可调 top_pct）
      - 收益单调性（按你定义：每日组号 vs 组收益 Spearman，再对时间均值）
    artifacts（绘图数据）：
      - rank_ic_series（序列图、分布图）
      - group_ret_by_day（10组日收益）
      - group_cumret（10组累计）
      - ls_series / ls_cumret（top-bottom）
      - mean_group_ret（平均10组未来收益）
    """

    def __init__(self, q: int = 10, top_pct: float = 0.2, long_high: bool = True):
        self._q = q
        self._top_pct = top_pct
        self._long_high = long_high

    @property
    def name(self) -> str:
        return "common_eval"

    @property
    def default_params(self):
        return {"q": self._q, "top_pct": self._top_pct, "long_high": self._long_high}

    def evaluate(
        self,
        factor: pd.Series,
        ret: pd.Series,
        q=10,
        top_pct=0.2,
        long_high=True,
        **_,
    ) -> EvalResult:
        # ---------- 0) 对齐与清洗 ----------
        common_idx = factor.index.intersection(ret.index)
        if common_idx.empty:
            return self._empty_result(factor.name, "empty intersection")

        factor = factor.loc[common_idx]
        ret = ret.loc[common_idx]

        valid_mask = factor.notna() & ret.notna()
        if not valid_mask.all():
            factor = factor[valid_mask]
            ret = ret[valid_mask]

        if factor.empty:
            return self._empty_result(factor.name, "empty after dropna")

        tmp = pd.DataFrame(
            {"factor": factor.astype(float), "ret": ret.astype(float)}
        ).sort_index()

        # ---------- 1) IC / Rank IC ----------
        def calc_ics(g):
            if len(g) < 2 or g["factor"].std() == 0 or g["ret"].std() == 0:
                return pd.Series({"ic": np.nan, "rank_ic": np.nan})
            ic = g["factor"].corr(g["ret"])
            rank_ic = g["factor"].corr(g["ret"], method="spearman")
            return pd.Series({"ic": ic, "rank_ic": rank_ic})

        ic_df = tmp.groupby(level="date").apply(calc_ics)
        ic_series = ic_df["ic"].dropna()
        rank_ic_series = ic_df["rank_ic"].dropna()

        def calc_stats(series: pd.Series):
            if len(series) < 2:
                return np.nan, np.nan, np.nan, np.nan
            mean = series.mean()
            std = series.std(ddof=1)
            if std <= 1e-8:
                return mean, std, np.nan, np.nan
            ir = mean / std
            t_val = mean / (std / np.sqrt(len(series)))
            return mean, std, ir, t_val

        ic_mean, ic_std, ic_ir, ic_t = calc_stats(ic_series)
        rank_ic_mean, rank_ic_std, rank_ic_ir, rank_ic_t = calc_stats(rank_ic_series)

        # ---------- 2) 分组收益（q组） ----------
        fac_for_group = factor if long_high else -factor
        tmp_group = pd.DataFrame({"factor": fac_for_group, "ret": ret}).sort_index()

        def get_group_ret(g, q_bins):
            if len(g) < q_bins:
                return pd.Series(dtype=float)
            try:
                labels = pd.qcut(g["factor"], q_bins, labels=False, duplicates="drop")
            except ValueError:
                return pd.Series(dtype=float)
            return g["ret"].groupby(labels).mean()

        # 结果：可能是 DataFrame(date x group)，也可能是 Series(date, group)
        group_ret_stack = tmp_group.groupby(level="date").apply(lambda g: get_group_ret(g, q))

        # ✅ 如果 apply 得到的是 Series（少见），才需要 unstack
        if isinstance(group_ret_stack, pd.Series):
            group_ret_by_day = group_ret_stack.unstack(level=-1).sort_index()
        else:
            # ✅ 常见情况：已经是 DataFrame
            group_ret_by_day = group_ret_stack.sort_index()
        
        if not group_ret_by_day.empty:
            # 补全列为 0..q-1，缺失用 NaN（利于统一绘图/比较）
            group_ret_by_day.columns = group_ret_by_day.columns.astype(int)
            group_ret_by_day = group_ret_by_day.reindex(columns=list(range(q)))

        if group_ret_by_day.empty:
            mean_group_ret = pd.Series(dtype=float)
            ls_series = pd.Series(dtype=float)
            group_cumret = pd.DataFrame()
            ls_cumret = pd.Series(dtype=float)
            monotonic_series = pd.Series(dtype=float)
            monotonic_mean = np.nan
        else:
            mean_group_ret = group_ret_by_day.mean()

            # 多空收益 top-bottom
            max_grp = group_ret_by_day.columns.max()
            min_grp = group_ret_by_day.columns.min()
            ls_series = group_ret_by_day[max_grp] - group_ret_by_day[min_grp]

            # 累计收益
            group_cumret = (1.0 + group_ret_by_day.fillna(0.0)).cumprod()
            ls_cumret = (1.0 + ls_series.fillna(0.0)).cumprod()

            # ---------- 3) 收益单调性 ----------
            def _mono_one_day(row: pd.Series):
                x = row.dropna()
                if len(x) < 2:
                    return np.nan
                idx = x.index.astype(float)  # 组号
                return st.spearmanr(idx, x.values).correlation

            monotonic_series = group_ret_by_day.apply(_mono_one_day, axis=1).dropna()
            monotonic_mean = monotonic_series.mean()

        # ---------- 4) top 20% 换手 ----------
        tmp_turnover = pd.DataFrame({"factor": fac_for_group}).sort_index()

        def _get_top_codes_safe(g):
            if len(g) == 0:
                return set()
            n = max(1, int(np.ceil(len(g) * top_pct)))
            largest = g.nlargest(n, "factor")
            if isinstance(largest.index, pd.MultiIndex):
                return set(largest.index.get_level_values(-1))  # 最后一个 level 当 asset id
            return set(largest.index)

        top_sets = tmp_turnover.groupby(level="date").apply(_get_top_codes_safe).sort_index()

        turnover_vals = []
        dates = top_sets.index
        prev_set = None
        for d in dates:
            cur_set = top_sets.loc[d]
            if prev_set is None or len(cur_set) == 0:
                turnover_vals.append(np.nan)
            else:
                overlap = len(cur_set & prev_set)
                turnover_vals.append(1.0 - overlap / len(cur_set))
            prev_set = cur_set

        turnover_series = pd.Series(turnover_vals, index=dates, name="top_turnover")
        top_turnover_mean = turnover_series.mean(skipna=True)

        # ---------- 5) 汇总输出 ----------
        ls_mean, ls_std, _, ls_t = calc_stats(ls_series.dropna()) if len(ls_series) else (np.nan, np.nan, np.nan, np.nan)

        metrics = {
            "ic_mean": ic_mean,
            "ic_std": ic_std,
            "ic_ir": ic_ir,
            "ic_t": ic_t,

            "rank_ic_mean": rank_ic_mean,
            "rank_ic_std": rank_ic_std,
            "rank_ic_ir": rank_ic_ir,
            "rank_ic_t": rank_ic_t,

            "top_turnover_20_mean": top_turnover_mean,
            "monotonic_mean": monotonic_mean,

            "group_ls_mean": ls_mean,
            "group_ls_t": ls_t,
        }

        artifacts = {
            # IC / RankIC 图
            "ic_series": ic_series,
            "rank_ic_series": rank_ic_series,
            "rank_ic_dist": rank_ic_series,   # 分布图直接用这条序列

            # 10组收益图
            "group_ret_by_day": group_ret_by_day,
            "group_cumret": group_cumret,
            "mean_group_ret": mean_group_ret,

            # top-bottom 图
            "ls_series": ls_series,
            "ls_cumret": ls_cumret,

            # 过程序列
            "top_turnover_series": turnover_series,
            "monotonic_series": monotonic_series,
        }

        f_name = str(factor.name) if factor.name is not None else "factor"

        return EvalResult(
            evaluator_name=self.name,
            factor_name=f_name,
            metrics=metrics,
            artifacts=artifacts,
        )

    def _empty_result(self, factor_name, msg):
        return EvalResult(
            evaluator_name=self.name,
            factor_name=str(factor_name or "factor"),
            metrics={},
            artifacts={},
            notes={"warning": msg},
        )


# =========== 注册内置评价器 ==========
add_evaluator(CommonFactorEvaluator(q=10, top_pct=0.2, long_high=True))
