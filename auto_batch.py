"""
自动因子入库脚本

功能：
1. 加载所有 auto 因子
2. 计算因子值
3. 评价因子表现
4. 根据入库规则自动入库
5. 生成评价报告
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime

# 导入所有 auto 因子
import factors.auto  # noqa: F401

from data_manager import LoacalDatasource
from factor_engine import list_factors, FactorEngine, FactorSpec
from evaluation.engine import EvaluatorEngine
from evaluation.interfaces import EvalResult
from factor_library import get_factor_library, get_config


class AutoFactorProcessor:
    """自动因子处理器"""
    
    def __init__(
        self,
        data_path: str = "./data/daily_price.parquet",
        start_date: str = "2020-01-01",
        end_date: str = "2026-01-01",
        horizons: Optional[List[int]] = None,
    ):
        """
        初始化处理器
        
        Args:
            data_path: 数据文件路径
            start_date: 开始日期
            end_date: 结束日期
            horizons: 评价周期列表
        """
        self.data_path = data_path
        self.start_date = start_date
        self.end_date = end_date
        self.horizons = horizons or [1, 5, 10, 20]
        
        # 初始化组件
        print("=" * 80)
        print("初始化自动因子处理器")
        print("=" * 80)
        
        # 加载数据
        print(f"\n加载数据: {data_path}")
        datasource = LoacalDatasource(file_path=data_path)
        self.df = datasource.load_data(start=start_date, end=end_date)
        print(f"✓ 数据加载完成: {len(self.df)} 行")
        
        # 初始化引擎
        self.factor_engine = FactorEngine()
        self.evaluator_engine = EvaluatorEngine()
        
        # 初始化因子库
        self.factor_lib = get_factor_library()
        config = get_config()
        self.admission_rule = self.factor_lib.admission_rule
        
        print(f"✓ 因子库初始化完成")
        print(f"  - 入库规则: IC >= {self.admission_rule.min_rank_ic}, IR >= {self.admission_rule.min_rank_ic_ir}")
        print(f"  - 评价周期: {self.horizons}")
    
    def get_auto_factors(self) -> List[FactorSpec]:
        """
        获取所有 auto 因子
        
        Returns:
            因子规格列表
        """
        all_factors = list(list_factors())
        
        # 获取已入库的因子名称
        existing_manual = {entry.spec.name for entry in self.factor_lib.manual_store.list_entries()}
        existing_auto = {entry.spec.name for entry in self.factor_lib.auto_store.list_entries()}
        existing_names = existing_manual | existing_auto
        
        # 筛选未入库的因子
        auto_factors = [f for f in all_factors if f.name not in existing_names]
        
        print(f"\n找到 {len(all_factors)} 个已注册因子")
        print(f"  - 已入库: {len(existing_names)} 个")
        print(f"  - 待处理: {len(auto_factors)} 个")
        
        return auto_factors
    
    def evaluate_factor(
        self,
        factor_spec: FactorSpec
    ) -> Dict[int, EvalResult]:
        """
        评价单个因子
        
        Args:
            factor_spec: 因子规格
            
        Returns:
            评价结果字典 {horizon: EvalResult}
        """
        print(f"\n{'=' * 80}")
        print(f"处理因子: {factor_spec.name} ({factor_spec.version})")
        print(f"{'=' * 80}")
        
        try:
            # 计算因子
            print(f"  [1/2] 计算因子值...")
            factor = self.factor_engine.compute_one(self.df, factor_spec)
            print(f"        ✓ 计算完成 (非空值: {factor.notna().sum()})")
            
            # 评价因子
            print(f"  [2/2] 评价因子表现...")
            reports = self.evaluator_engine.evaluate_multi_horizons(
                df=self.df,
                factor=factor,
                horizons=self.horizons,
                evaluator="common_eval"
            )
            print(f"        ✓ 评价完成")
            
            return reports
            
        except Exception as e:
            print(f"        ✗ 错误: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def try_auto_admit(
        self,
        factor_spec: FactorSpec,
        reports: Dict[int, EvalResult]
    ) -> bool:
        """
        尝试自动入库
        
        Args:
            factor_spec: 因子规格
            reports: 评价结果
            
        Returns:
            是否入库成功
        """
        if not reports:
            print(f"\n  [入库判断] 跳过（无评价结果）")
            return False
        
        # 按照从短到长的顺序检查每个周期，找到第一个通过的
        print(f"\n  [入库判断] 检查各周期评价结果")
        
        for horizon in sorted(reports.keys()):
            eval_result = reports[horizon]
            metrics = eval_result.metrics
            rank_ic = metrics.get("rank_ic_mean", 0.0)
            rank_ic_ir = metrics.get("rank_ic_ir", 0.0)
            
            # 判断是否通过入库规则（传递 metrics 字典）
            is_pass = self.admission_rule.is_pass(metrics)
            
            print(f"        - {horizon:>2}日: Rank IC={rank_ic:>7.4f}, IR={rank_ic_ir:>6.4f}  {'✓ 通过' if is_pass else '✗ 未通过'}")
            
            # 找到第一个通过的周期就使用它
            if is_pass:
                print(f"\n  [入库决策] 使用 {horizon} 日评价结果进行入库")
                
                # 尝试自动入库
                success = self.factor_lib.auto_admit_from_eval(
                    spec=factor_spec,
                    eval_result=eval_result,
                    description=f"自动挖掘因子 (周期: {horizon}日, Rank IC: {rank_ic:.4f}, IR: {rank_ic_ir:.4f})",
                    tags=["auto", "quantitative", f"horizon_{horizon}"]
                )
                
                if success:
                    print(f"        ✓ 入库成功！")
                else:
                    print(f"        ✗ 入库失败")
                
                return success
        
        # 所有周期都未通过
        print(f"\n  [入库决策] 所有周期均未达到入库标准，放弃入库")
        return False
    
    def print_summary(
        self,
        factor_spec: FactorSpec,
        reports: Dict[int, EvalResult]
    ):
        """
        打印因子评价摘要
        
        Args:
            factor_spec: 因子规格
            reports: 评价结果
        """
        print(f"\n  [评价摘要]")
        print(f"  {'周期':>6} | {'Rank IC':>10} | {'IC IR':>10} | {'多空收益':>10} | {'换手率':>10}")
        print(f"  {'-' * 65}")
        
        for horizon, report in sorted(reports.items()):
            m = report.metrics
            print(f"  {horizon:>4}日 | "
                  f"{m.get('rank_ic_mean', 0):>10.4f} | "
                  f"{m.get('rank_ic_ir', 0):>10.4f} | "
                  f"{m.get('group_ls_mean', 0):>10.4f} | "
                  f"{m.get('top_turnover_20_mean', 0):>10.4f}")
    
    def process_all(self) -> Dict[str, bool]:
        """
        处理所有 auto 因子
        
        Returns:
            处理结果字典 {factor_name: success}
        """
        auto_factors = self.get_auto_factors()
        
        if not auto_factors:
            print("\n没有待处理的因子")
            return {}
        
        results = {}
        success_count = 0
        
        for i, factor_spec in enumerate(auto_factors, 1):
            print(f"\n\n{'#' * 80}")
            print(f"# 进度: {i}/{len(auto_factors)}")
            print(f"{'#' * 80}")
            
            # 评价因子
            reports = self.evaluate_factor(factor_spec)
            
            if reports:
                # 打印摘要
                self.print_summary(factor_spec, reports)
                
                # 尝试自动入库
                success = self.try_auto_admit(factor_spec, reports)
                results[factor_spec.name] = success
                
                if success:
                    success_count += 1
            else:
                results[factor_spec.name] = False
        
        # 打印最终统计
        print(f"\n\n{'=' * 80}")
        print(f"处理完成")
        print(f"{'=' * 80}")
        print(f"  - 总共处理: {len(auto_factors)} 个因子")
        print(f"  - 成功入库: {success_count} 个")
        print(f"  - 未通过: {len(auto_factors) - success_count} 个")
        
        # 显示因子库统计
        stats = self.factor_lib.get_factor_count()
        print(f"\n当前因子库统计:")
        print(f"  - 手动入库: {stats['manual']} 个")
        print(f"  - 自动入库: {stats['auto']} 个")
        print(f"  - 总计: {stats['total']} 个")
        
        return results


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("自动因子入库脚本")
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        # 创建处理器
        processor = AutoFactorProcessor(
            data_path="./data/daily_price.parquet",
            start_date="2020-01-01",
            end_date="2026-01-01",
            horizons=[1, 5, 10, 20]
        )
        
        # 处理所有因子
        results = processor.process_all()
        
        print("\n" + "=" * 80)
        print("脚本执行完成")
        print("=" * 80)
        
        return 0
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
