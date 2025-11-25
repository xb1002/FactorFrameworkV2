# evaluation/builtins.py
from __future__ import annotations

import os
import pandas as pd
import numpy as np
import scipy.stats as st
import matplotlib.pyplot as plt
from typing import Dict, Any
from dataclasses import dataclass, field

from .interfaces import IEvaluator, EvalResult
from .registry import add_evaluator


@dataclass
class CommonFactorEvalResult(EvalResult):
    """
    CommonFactorEvaluator 的专用结果类
    
    继承自 EvalResult，实现了针对通用因子评价的绘图功能
    """
    horizon: int = 1  # 添加 horizon 字段
    
    def plot_artifacts(
        self,
        show_fig: bool = False,
        figsize: tuple | None = None,
        dpi: int = 100,
        style: str = "default",
        save_path: str | None = None,
        # 子类特定参数
        horizon: int | None = None,
        show_monthly_ic_labels: bool | None = None,
        figsize_rank_ic: tuple | None = None,
        figsize_rank_ic_dist: tuple | None = None,
        figsize_rank_ic_monthly: tuple | None = None,
        figsize_group_cumret: tuple | None = None,
        figsize_ls_cumret: tuple | None = None,
        figsize_mean_group_ret: tuple | None = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        根据 artifacts 绘制所有因子评价图表
        
        Args:
            show_fig: 是否显示图表（默认False不显示）
            figsize: 全局图表尺寸，会被具体的 figsize_* 参数覆盖
            dpi: 图表分辨率
            style: matplotlib样式
            save_path: 保存路径，如果指定则保存所有图表
            horizon: 评价的时间跨度（用于图表标题）
            show_monthly_ic_labels: 是否在月频IC柱状图上显示数值标签，None时自动判断
            figsize_*: 各个具体图表的尺寸，优先级高于全局figsize
        
        Returns:
            Dict[str, plt.Figure]: 包含所有图表的字典
        """

        artifacts = self.artifacts
        factor_name = self.factor_name or "factor"
        
        # 使用存储的 horizon,如果没有传入的话
        if horizon is None:
            horizon = self.horizon
        
        # 应用matplotlib样式
        if style != "default":
            plt.style.use(style)
        
        # 设置默认尺寸
        default_figsize = figsize or (12, 4)
        figsize_rank_ic = figsize_rank_ic or default_figsize
        figsize_rank_ic_dist = figsize_rank_ic_dist or (12, 4)
        figsize_rank_ic_monthly = figsize_rank_ic_monthly or (12, 5)
        figsize_group_cumret = figsize_group_cumret or (12, 6)
        figsize_ls_cumret = figsize_ls_cumret or default_figsize
        figsize_mean_group_ret = figsize_mean_group_ret or (12, 5)
        
        figures = {}
        
        # 检查是否有足够的数据
        if not artifacts or "rank_ic_series" not in artifacts:
            return figures
        
        rank_ic_series = artifacts["rank_ic_series"]
        
        # 创建保存目录
        if save_path:
            os.makedirs(save_path, exist_ok=True)
        
        # 1. Rank IC 序列图
        fig1, ax1 = plt.subplots(figsize=figsize_rank_ic)
        rank_ic_series.plot(ax=ax1, label='Rank IC', alpha=0.7)
        ax1.axhline(0, color='black', linestyle='--', linewidth=0.8)
        ax1.axhline(rank_ic_series.mean(), color='red', linestyle='--', 
                    linewidth=0.8, label=f'均值: {rank_ic_series.mean():.4f}')
        ax1.set_title(f'{factor_name} - Rank IC 序列图 (Horizon={horizon}d)', 
                      fontsize=14, fontweight='bold')
        ax1.set_xlabel('日期', fontsize=12)
        ax1.set_ylabel('Rank IC', fontsize=12)
        ax1.legend()
        ax1.grid(alpha=0.3)
        fig1.tight_layout()
        
        if save_path:
            fig1.savefig(os.path.join(save_path, f'{factor_name}_rank_ic_series.png'), dpi=dpi, bbox_inches='tight')
        
        if not show_fig:
            plt.close(fig1)
        
        figures['rank_ic_series'] = fig1
        
        # 2. Rank IC 分布图
        fig2, ax2 = plt.subplots(figsize=figsize_rank_ic_dist)
        rank_ic_series.hist(bins=50, ax=ax2, alpha=0.7, edgecolor='black')
        ax2.axvline(rank_ic_series.mean(), color='red', linestyle='--', 
                    linewidth=2, label=f'均值: {rank_ic_series.mean():.4f}')
        ax2.axvline(0, color='black', linestyle='--', linewidth=1)
        ax2.set_title(f'{factor_name} - Rank IC 分布图 (Horizon={horizon}d)', 
                      fontsize=14, fontweight='bold')
        ax2.set_xlabel('Rank IC', fontsize=12)
        ax2.set_ylabel('频数', fontsize=12)
        ax2.legend()
        ax2.grid(alpha=0.3)
        fig2.tight_layout()
        
        if save_path:
            fig2.savefig(os.path.join(save_path, f'{factor_name}_rank_ic_dist.png'), dpi=dpi, bbox_inches='tight')
        
        if not show_fig:
            plt.close(fig2)
        
        figures['rank_ic_dist'] = fig2
        
        # 3. 月频 Rank IC 柱状图
        fig3, ax3 = plt.subplots(figsize=figsize_rank_ic_monthly)
        monthly_ic = rank_ic_series.resample('ME').mean()  # 使用 'ME' 替代已弃用的 'M'
        x_pos = range(len(monthly_ic))
        colors = ['red' if v < 0 else 'green' for v in monthly_ic]
        bars = ax3.bar(x_pos, monthly_ic, color=colors, alpha=0.7, 
                       edgecolor='black', width=0.8)
        
        ax3.set_xticks(x_pos)
        ax3.set_xticklabels([d.strftime('%Y-%m') for d in monthly_ic.index], 
                            rotation=45, ha='right')
        ax3.axhline(0, color='black', linestyle='-', linewidth=0.8)
        ax3.axhline(rank_ic_series.mean(), color='blue', linestyle='--', 
                    linewidth=1.5, label=f'整体均值: {rank_ic_series.mean():.4f}')
        ax3.set_title(f'{factor_name} - 月频 Rank IC (Horizon={horizon}d)', 
                      fontsize=14, fontweight='bold')
        ax3.set_xlabel('月份', fontsize=12)
        ax3.set_ylabel('月均 Rank IC', fontsize=12)
        ax3.legend()
        ax3.grid(alpha=0.3, axis='y')
        
        # 是否显示数值标签
        if show_monthly_ic_labels is None:
            show_monthly_ic_labels = len(monthly_ic) <= 24
        
        if show_monthly_ic_labels:
            for bar, val in zip(bars, monthly_ic):
                height = bar.get_height()
                ax3.text(bar.get_x() + bar.get_width()/2., height,
                        f'{val:.3f}',
                        ha='center', va='bottom' if height > 0 else 'top', 
                        fontsize=8)
        
        fig3.tight_layout()
        
        if save_path:
            fig3.savefig(os.path.join(save_path, f'{factor_name}_rank_ic_monthly.png'), dpi=dpi, bbox_inches='tight')
        
        if not show_fig:
            plt.close(fig3)
        
        figures['rank_ic_monthly'] = fig3
        
        # 4. 10组累计收益图
        if "group_cumret" in artifacts and not artifacts["group_cumret"].empty:
            fig4, ax4 = plt.subplots(figsize=figsize_group_cumret)
            group_cumret = artifacts["group_cumret"]
            for col in group_cumret.columns:
                group_cumret[col].plot(ax=ax4, label=f'第{col+1}组', alpha=0.7)
            ax4.set_title(f'{factor_name} - 10组累计收益 (Horizon={horizon}d)', 
                          fontsize=14, fontweight='bold')
            ax4.set_xlabel('日期', fontsize=12)
            ax4.set_ylabel('累计收益', fontsize=12)
            ax4.legend(loc='best', ncol=2)
            ax4.grid(alpha=0.3)
            fig4.tight_layout()
            
            if save_path:
                fig4.savefig(os.path.join(save_path, f'{factor_name}_group_cumret.png'), dpi=dpi, bbox_inches='tight')
            
            if not show_fig:
                plt.close(fig4)
            
            figures['group_cumret'] = fig4
        
        # 5. Top-Bottom 累计收益图
        if "ls_cumret" in artifacts and not artifacts["ls_cumret"].empty:
            fig5, ax5 = plt.subplots(figsize=figsize_ls_cumret)
            ls_cumret = artifacts["ls_cumret"]
            ls_cumret.plot(ax=ax5, label='Top-Bottom 多空组合', 
                          color='purple', linewidth=2, alpha=0.8)
            ax5.axhline(1, color='black', linestyle='--', linewidth=0.8)
            ax5.set_title(f'{factor_name} - Top-Bottom 累计收益 (Horizon={horizon}d)', 
                          fontsize=14, fontweight='bold')
            ax5.set_xlabel('日期', fontsize=12)
            ax5.set_ylabel('累计收益', fontsize=12)
            ax5.legend()
            ax5.grid(alpha=0.3)
            fig5.tight_layout()
            
            if save_path:
                fig5.savefig(os.path.join(save_path, f'{factor_name}_ls_cumret.png'), dpi=dpi, bbox_inches='tight')
            
            if not show_fig:
                plt.close(fig5)
            
            figures['ls_cumret'] = fig5
        
        # 6. 平均10组未来收益柱状图
        if "mean_group_ret" in artifacts and not artifacts["mean_group_ret"].empty:
            fig6, ax6 = plt.subplots(figsize=figsize_mean_group_ret)
            mean_group_ret = artifacts["mean_group_ret"]
            x_pos = range(len(mean_group_ret))
            colors = ['red' if v < 0 else 'green' for v in mean_group_ret]
            bars = ax6.bar(x_pos, mean_group_ret, color=colors, 
                          alpha=0.7, edgecolor='black')
            ax6.set_title(f'{factor_name} - 平均10组未来收益 (Horizon={horizon}d)', 
                          fontsize=14, fontweight='bold')
            ax6.set_xlabel('分组 (0=最低, 9=最高)', fontsize=12)
            ax6.set_ylabel('平均收益率', fontsize=12)
            ax6.set_xticks(x_pos)
            ax6.set_xticklabels([f'G{i}' for i in range(len(mean_group_ret))])
            ax6.axhline(0, color='black', linestyle='-', linewidth=0.8)
            ax6.grid(alpha=0.3, axis='y')
            
            for i, (bar, val) in enumerate(zip(bars, mean_group_ret)):
                height = bar.get_height()
                ax6.text(bar.get_x() + bar.get_width()/2., height,
                        f'{val:.4f}',
                        ha='center', va='bottom' if height > 0 else 'top', 
                        fontsize=9)
            
            fig6.tight_layout()
            
            if save_path:
                fig6.savefig(os.path.join(save_path, f'{factor_name}_mean_group_ret.png'), dpi=dpi, bbox_inches='tight')
            
            if not show_fig:
                plt.close(fig6)
            
            figures['mean_group_ret'] = fig6
        
        # 恢复默认样式
        if style != "default":
            plt.style.use('default')
        
        return figures


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
        horizon=1,
        **_,
    ) -> EvalResult:
        # ---------- 0) 对齐与清洗 ----------
        common_idx = factor.index.intersection(ret.index)
        if common_idx.empty:
            return self._empty_result(factor.name, "empty intersection")

        factor = factor.loc[common_idx]
        ret = ret.loc[common_idx]
        
        # ✅ 收益摊销：将 horizon 期收益转换为日均收益
        if horizon > 1:
            ret = ret / horizon

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

        return CommonFactorEvalResult(
            evaluator_name=self.name,
            factor_name=f_name,
            metrics=metrics,
            artifacts=artifacts,
            horizon=horizon,  # 传递 horizon 用于绘图
        )

    def _empty_result(self, factor_name, msg):
        return CommonFactorEvalResult(
            evaluator_name=self.name,
            factor_name=str(factor_name or "factor"),
            metrics={},
            artifacts={},
            notes={"warning": msg},
        )


# =========== 注册内置评价器 ==========
add_evaluator(CommonFactorEvaluator(q=10, top_pct=0.2, long_high=True))
