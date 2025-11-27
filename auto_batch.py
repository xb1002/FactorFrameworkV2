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
import json
import hashlib
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Set
import pandas as pd
from datetime import datetime

# 导入所有 auto 因子
import factors.auto  # noqa: F401

from data_manager import LoacalDatasource
from factor_engine import list_factors, FactorEngine, FactorSpec
from evaluation.engine import EvaluatorEngine
from evaluation.interfaces import EvalResult
from app import get_factor_library, get_config


class AutoFactorProcessor:
    """自动因子处理器"""
    
    def __init__(
        self,
        data_path: str = "./data/daily_price.parquet",
        start_date: str = "2020-01-01",
        end_date: str = "2026-01-01",
        horizons: Optional[List[int]] = None,
        hash_record_path: str = "./factor_hash_records.json",
        force_reprocess: bool = False,
        factor_names: Optional[List[str]] = None,
    ):
        """
        初始化处理器
        
        Args:
            data_path: 数据文件路径
            start_date: 开始日期
            end_date: 结束日期
            horizons: 评价周期列表
            hash_record_path: hash 记录文件路径
            force_reprocess: 是否强制重新处理所有因子
            factor_names: 指定处理的因子名称列表，None 表示处理所有因子
        """
        self.data_path = data_path
        self.start_date = start_date
        self.end_date = end_date
        self.horizons = horizons or [1, 5, 10, 20]
        self.hash_record_path = Path(hash_record_path)
        self.force_reprocess = force_reprocess
        self.factor_names = set(factor_names) if factor_names else None
        
        # Hash 记录管理
        self.hash_records: Dict[str, str] = self._load_hash_records()
        
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
        print(f"  - 入库规则: |IC| >= {self.admission_rule.min_rank_ic}, |IR| >= {self.admission_rule.min_rank_ic_ir}, "
              f"换手率/周期 <= {self.admission_rule.max_top_turnover_20_mean}, |单调性| >= {self.admission_rule.min_monotonic_mean}")
        print(f"  - 评价周期: {self.horizons}")
        print(f"  - Hash 记录: {len(self.hash_records)} 个已处理因子")
        print(f"  - 强制重新处理: {'是' if self.force_reprocess else '否'}")
        if self.factor_names:
            print(f"  - 指定因子: {len(self.factor_names)} 个")
        print(f"  - Hash 记录: {len(self.hash_records)} 个已处理因子")
        print(f"  - 强制重新处理: {'是' if self.force_reprocess else '否'}")
        if self.factor_names:
            print(f"  - 指定因子: {len(self.factor_names)} 个")
    
    @staticmethod
    def _compute_factor_hash(factor_spec: FactorSpec) -> str:
        """
        计算因子规格的 hash 值
        
        Args:
            factor_spec: 因子规格
            
        Returns:
            Hash 字符串
        """
        # 构造用于计算 hash 的字符串，包含因子的关键属性
        hash_content = f"{factor_spec.name}|{factor_spec.version}|{factor_spec.func.__code__.co_code}"
        return hashlib.md5(hash_content.encode()).hexdigest()
    
    def _load_hash_records(self) -> Dict[str, str]:
        """
        加载 hash 记录文件
        
        Returns:
            Hash 记录字典 {factor_name: hash_value}
        """
        if not self.hash_record_path.exists():
            return {}
        
        try:
            with open(self.hash_record_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"警告: 无法加载 hash 记录文件 ({e})，将使用空记录")
            return {}
    
    def _save_hash_records(self):
        """
        保存 hash 记录到文件
        """
        try:
            # 确保目录存在
            self.hash_record_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.hash_record_path, 'w', encoding='utf-8') as f:
                json.dump(self.hash_records, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"        ⚠ 警告: 无法保存 hash 记录 ({e})")
    
    def _should_process_factor(self, factor_spec: FactorSpec) -> tuple:
        """
        判断是否需要处理该因子
        
        Args:
            factor_spec: 因子规格
            
        Returns:
            (是否需要处理, 原因说明)
        """
        # 如果强制重新处理，直接返回 True
        if self.force_reprocess:
            return True, "强制重新处理"
        
        # 计算当前 hash 值
        current_hash = self._compute_factor_hash(factor_spec)
        
        # 检查是否有历史记录
        if factor_spec.name not in self.hash_records:
            return True, "首次处理"
        
        # 对比 hash 值
        old_hash = self.hash_records[factor_spec.name]
        if old_hash != current_hash:
            return True, f"代码已变更 (旧: {old_hash[:8]}..., 新: {current_hash[:8]}...)"
        
        return False, f"代码未变更 (hash: {current_hash[:8]}...)"
    
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
        
        # 如果指定了因子列表，进一步筛选
        if self.factor_names:
            auto_factors = [f for f in auto_factors if f.name in self.factor_names]
        
        print(f"\n找到 {len(all_factors)} 个已注册因子")
        print(f"  - 已入库: {len(existing_names)} 个")
        if self.factor_names:
            print(f"  - 指定处理: {len(self.factor_names)} 个")
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
            
            # 判断是否通过入库规则（传递 metrics 字典和 horizon）
            is_pass = self.admission_rule.is_pass(metrics, horizon)
            
            # print(f"        - {horizon:>2}日: Rank IC={rank_ic:>7.4f}, IR={rank_ic_ir:>6.4f}  {'✓ 通过' if is_pass else '✗ 未通过'}")
            # Rank IC 和 IR，换手率，单调性等指标综合判断
            print(f"        - {horizon:>2}日: Rank IC={rank_ic:>7.4f}, IR={rank_ic_ir:>6.4f}, "
                  f"换手率/周期={metrics.get('top_turnover_20_mean', 0.0)/horizon:>7.4f}, "
                  f"|单调性|={metrics.get('monotonic_mean', 0.0):>7.4f}  "
                  f"{'✓ 通过' if is_pass else '✗ 未通过'}")
            
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
        skipped_count = 0
        
        for i, factor_spec in enumerate(auto_factors, 1):
            print(f"\n\n{'#' * 80}")
            print(f"# 进度: {i}/{len(auto_factors)}")
            print(f"{'#' * 80}")
            
            # 检查是否需要处理
            should_process, reason = self._should_process_factor(factor_spec)
            
            if not should_process:
                print(f"\n跳过因子: {factor_spec.name} ({factor_spec.version})")
                print(f"  原因: {reason}")
                results[factor_spec.name] = None  # None 表示跳过
                skipped_count += 1
                continue
            
            print(f"\n处理原因: {reason}")
            
            # 评价因子
            reports = self.evaluate_factor(factor_spec)
            
            if reports:
                # 打印摘要
                self.print_summary(factor_spec, reports)
                
                # 尝试自动入库
                success = self.try_auto_admit(factor_spec, reports)
                results[factor_spec.name] = success
                
                # 更新 hash 记录（无论是否入库成功，都记录已处理）
                current_hash = self._compute_factor_hash(factor_spec)
                self.hash_records[factor_spec.name] = current_hash
                
                # 立即保存 hash 记录
                self._save_hash_records()
                print(f"        ✓ Hash 已更新: {current_hash[:16]}...")
                
                if success:
                    success_count += 1
            else:
                results[factor_spec.name] = False
        
        # 打印最终统计
        print(f"\n\n{'=' * 80}")
        print(f"处理完成")
        print(f"{'=' * 80}")
        print(f"  - 总共待处理: {len(auto_factors)} 个因子")
        print(f"  - 跳过未变更: {skipped_count} 个")
        print(f"  - 实际处理: {len(auto_factors) - skipped_count} 个")
        print(f"  - 成功入库: {success_count} 个")
        print(f"  - 未通过: {len(auto_factors) - skipped_count - success_count} 个")
        
        # 显示因子库统计
        stats = self.factor_lib.get_factor_count()
        print(f"\n当前因子库统计:")
        print(f"  - 手动入库: {stats['manual']} 个")
        print(f"  - 自动入库: {stats['auto']} 个")
        print(f"  - 总计: {stats['total']} 个")
        
        return results


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="自动因子入库脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 处理所有因子（使用默认参数）
  python auto_batch.py
  
  # 强制重新处理所有因子
  python auto_batch.py --force
  
  # 只处理指定的因子
  python auto_batch.py --factors momentum_5d_v1 momentum_10d_v1
  
  # 指定时间范围
  python auto_batch.py --start-date 2022-01-01 --end-date 2024-01-01
  
  # 指定评价周期
  python auto_batch.py --horizons 5 10 20
  
  # 指定 hash 记录文件路径
  python auto_batch.py --hash-record ./my_hash_records.json
        """
    )
    
    parser.add_argument(
        "--data-path",
        type=str,
        default="./data/daily_price.parquet",
        help="数据文件路径 (默认: ./data/daily_price.parquet)"
    )
    
    parser.add_argument(
        "--start-date",
        type=str,
        default="2020-01-01",
        help="开始日期 (默认: 2020-01-01)"
    )
    
    parser.add_argument(
        "--end-date",
        type=str,
        default="2026-01-01",
        help="结束日期 (默认: 2026-01-01)"
    )
    
    parser.add_argument(
        "--horizons",
        type=int,
        nargs="+",
        default=[1, 5, 10, 20],
        help="评价周期列表 (默认: 1 5 10 20)"
    )
    
    parser.add_argument(
        "--hash-record",
        type=str,
        default="./factor_hash_records.json",
        help="hash 记录文件路径 (默认: ./factor_hash_records.json)"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新处理所有因子（忽略 hash 记录）"
    )
    
    parser.add_argument(
        "--factors",
        type=str,
        nargs="+",
        default=None,
        help="指定要处理的因子名称列表（默认处理所有因子）"
    )
    
    return parser.parse_args()


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()
    
    print("\n" + "=" * 80)
    print("自动因子入库脚本")
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        # 创建处理器
        processor = AutoFactorProcessor(
            data_path=args.data_path,
            start_date=args.start_date,
            end_date=args.end_date,
            horizons=args.horizons,
            hash_record_path=args.hash_record,
            force_reprocess=args.force,
            factor_names=args.factors,
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
