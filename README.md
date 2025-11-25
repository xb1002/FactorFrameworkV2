# FactorFramework

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

一个轻量级、模块化的量化因子研究框架，用于因子开发、计算和评价。

## 📋 目录

- [特性](#特性)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [核心模块](#核心模块)
  - [数据管理器 (data_manager)](#数据管理器-data_manager)
  - [因子引擎 (factor_engine)](#因子引擎-factor_engine)
  - [评价引擎 (evaluation)](#评价引擎-evaluation)
- [使用示例](#使用示例)
  - [加载数据](#加载数据)
  - [注册和计算因子](#注册和计算因子)
  - [因子评价](#因子评价)
- [扩展开发](#扩展开发)
- [依赖项](#依赖项)
- [贡献](#贡献)
- [许可证](#许可证)

## ✨ 特性

- **模块化设计**：数据管理、因子计算、评价模块完全解耦
- **装饰器注册**：简洁的因子注册机制，支持元数据管理
- **灵活的数据源**：可扩展的数据源接口，支持本地文件（CSV、Parquet）
- **丰富的评价指标**：IC、Rank IC、分组收益、多空收益、换手率等
- **可视化支持**：内置多种因子评价图表（IC序列图、分组累计收益图等）
- **多周期评价**：支持多个持有期（horizon）的因子表现评价
- **类型注解**：完整的类型提示，提升代码可读性和 IDE 支持

## 📁 项目结构

```
FactorFramework/
├── data/                      # 数据文件目录
│   └── daily_price.parquet   # 示例：日频行情数据
├── data_manager/              # 数据管理模块
│   ├── __init__.py
│   ├── interfaces.py         # 数据源接口定义
│   └── datasource.py         # 本地数据源实现
├── factor_engine/             # 因子引擎模块
│   ├── __init__.py
│   ├── interfaces.py         # 因子接口和类型定义
│   ├── registry.py           # 因子注册表
│   └── engine.py             # 因子计算引擎
├── evaluation/                # 评价引擎模块
│   ├── __init__.py
│   ├── interfaces.py         # 评价器接口定义
│   ├── registry.py           # 评价器注册表
│   ├── forward_return.py     # 未来收益计算
│   ├── builtins.py           # 内置评价器
│   └── engine.py             # 评价引擎
├── main.ipynb                 # 使用示例 Notebook
└── README.md                  # 项目说明文档
```

## 🚀 快速开始

### 安装依赖

```bash
pip install pandas numpy scipy matplotlib
```

### 基础使用流程

```python
import pandas as pd
from data_manager import LoacalDatasource
from factor_engine import register_factor, FactorEngine
from evaluation.engine import EvaluatorEngine

# 1. 加载数据
datasource = LoacalDatasource(file_path="./data/daily_price.parquet")
df = datasource.load_data(start="2020-01-01", end="2023-12-31")

# 2. 注册因子
@register_factor(
    name="momentum_20",
    required_fields=["close"],
)
def momentum_factor(df: pd.DataFrame) -> pd.Series:
    return df["close"].groupby(level="code").pct_change(20)

# 3. 计算因子
factor_engine = FactorEngine()
factor = factor_engine.compute_one(df, "momentum_20")

# 4. 评价因子
evaluator_engine = EvaluatorEngine()
reports = evaluator_engine.evaluate_multi_horizons(
    df=df,
    factor=factor,
    horizons=[1, 5, 10],
    evaluator="common_eval"
)

# 5. 查看结果
for horizon, report in reports.items():
    print(f"=== 持有期: {horizon} 天 ===")
    print(report.metrics)
    report.plot_artifacts(show_fig=True)
```

## 🔧 核心模块

### 数据管理器 (data_manager)

数据管理模块提供统一的数据接口，支持多种数据源扩展。

#### 接口定义

```python
class IDataSource(ABC):
    @abstractmethod
    def load_data(self, start, end, fields, codes) -> pd.DataFrame:
        """返回 MultiIndex(date, code) 的数据"""
```

#### 本地数据源

```python
from data_manager import LoacalDatasource

# 初始化数据源
datasource = LoacalDatasource(file_path="./data/daily_price.parquet")

# 加载数据
df = datasource.load_data(
    start="2020-01-01",
    end="2023-12-31",
    fields=["open", "high", "low", "close", "volume"],
    codes=["000001.SZ", "600000.SH"]
)
```

**数据格式要求**：
- 索引：`MultiIndex(date, code)`，其中 date 为日期，code 为标的代码
- 列：至少包含价格字段（如 `close`）

### 因子引擎 (factor_engine)

因子引擎负责因子的注册、管理和计算。

#### 因子注册

使用装饰器注册因子：

```python
from factor_engine import register_factor

@register_factor(
    name="custom_factor",           # 因子名称
    required_fields=["close"],      # 必需字段
    params={"window": 20},          # 默认参数
    version="v1",                   # 版本号
    force_update=False              # 是否强制更新
)
def custom_factor(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    自定义因子函数
    
    Args:
        df: MultiIndex(date, code) 的 DataFrame
        window: 参数示例
    
    Returns:
        pd.Series: MultiIndex(date, code) 的因子值
    """
    return df["close"].groupby(level="code").rolling(window).mean()
```

#### 因子计算

```python
from factor_engine import FactorEngine

engine = FactorEngine()

# 计算单个因子
factor = engine.compute_one(df, "custom_factor", window=30)

# 批量计算因子
factors_df = engine.compute_all(
    df,
    factors=["momentum_20", "custom_factor"],
    per_factor_params={"momentum_20": {"window": 30}}
)
```

#### 因子接口规范

所有因子函数必须满足以下签名：

```python
def factor_func(df: pd.DataFrame, **params) -> pd.Series:
    """
    - 输入: df 的 index 必须是 MultiIndex(date, code)
    - 输出: Series 的 index 必须和 df.index 对齐
    """
```

### 评价引擎 (evaluation)

评价引擎提供因子表现的全方位评价功能。

#### 内置评价器：common_eval

`common_eval` 是通用因子评价器，提供以下指标：

**数值指标 (metrics)**：
- `ic_mean`, `ic_std`, `ic_ir`, `ic_t`：普通 IC 指标
- `rank_ic_mean`, `rank_ic_std`, `rank_ic_ir`, `rank_ic_t`：Rank IC 指标
- `top_turnover_20_mean`：Top 20% 持仓换手率
- `monotonic_mean`：收益单调性（分组收益与组号的 Spearman 相关系数）
- `group_ls_mean`, `group_ls_t`：多空组合收益及 t 统计量

**可视化数据 (artifacts)**：
- `rank_ic_series`：Rank IC 时间序列
- `group_ret_by_day`：10 组日收益
- `group_cumret`：10 组累计收益
- `ls_cumret`：多空组合累计收益
- `mean_group_ret`：各组平均收益

#### 单周期评价

```python
from evaluation.engine import EvaluatorEngine

evaluator = EvaluatorEngine()

# 单一持有期评价
result = evaluator.evaluate_one_horizon(
    df=df,
    factor=factor,
    horizon=5,                    # 持有期 5 天
    evaluator="common_eval",      # 评价器名称
    price_col="close",            # 价格列
    kind="simple"                 # 收益率类型：simple 或 log
)

print(result.metrics)             # 查看指标
result.plot_artifacts(show_fig=True)  # 绘制图表
```

#### 多周期评价

```python
# 多个持有期评价
reports = evaluator.evaluate_multi_horizons(
    df=df,
    factor=factor,
    horizons=[1, 5, 10, 20],      # 多个持有期
    evaluator="common_eval"
)

# 查看各周期结果
for horizon, report in reports.items():
    print(f"=== 持有期: {horizon} 天 ===")
    print(f"Rank IC: {report.metrics['rank_ic_mean']:.4f}")
    print(f"Rank ICIR: {report.metrics['rank_ic_ir']:.4f}")
```

#### 可视化

```python
# 显示所有图表
report.plot_artifacts(show_fig=True)

# 自定义图表样式
figures = report.plot_artifacts(
    show_fig=False,
    figsize=(14, 6),
    dpi=150,
    style='seaborn'
)

# 保存图表
report.plot_artifacts(
    save_path="./output/plots",
    dpi=300
)
```

**内置图表**：
1. **Rank IC 序列图**：展示因子 Rank IC 的时序变化
2. **Rank IC 分布图**：展示 Rank IC 的统计分布
3. **月频 Rank IC 柱状图**：按月汇总的 Rank IC 表现
4. **10 组累计收益图**：展示因子分组后的累计收益走势
5. **Top-Bottom 累计收益图**：多空组合的累计收益
6. **平均 10 组未来收益柱状图**：各分组的平均收益对比

## 💡 使用示例

### 加载数据

```python
from data_manager import LoacalDatasource

# 从本地加载数据
datasource = LoacalDatasource(file_path="./data/daily_price.parquet")
df = datasource.load_data(start="2020-01-01", end="2023-12-31")

# 查看数据结构
print(df.index.names)     # ['date', 'code']
print(df.columns.tolist())  # ['open', 'high', 'low', 'close', 'volume', ...]
```

### 注册和计算因子

#### 示例 1：动量因子

```python
from factor_engine import register_factor, FactorEngine

@register_factor(
    name="momentum_20",
    required_fields=["close"],
)
def momentum_20(df: pd.DataFrame) -> pd.Series:
    """20 日动量因子"""
    return df["close"].groupby(level="code").pct_change(20)

# 计算因子
engine = FactorEngine()
factor = engine.compute_one(df, "momentum_20")
```

#### 示例 2：波动率因子

```python
@register_factor(
    name="volatility_20",
    required_fields=["close"],
    params={"window": 20}
)
def volatility_factor(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """滚动波动率因子"""
    return df["close"].groupby(level="code").pct_change().rolling(window).std()

# 使用自定义参数
factor = engine.compute_one(df, "volatility_20", window=30)
```

#### 示例 3：复合因子

```python
@register_factor(
    name="liquidity_momentum_deviation",
    required_fields=["open", "close", "amount"],
    force_update=True,
)
def liquidity_momentum_deviation_factor(df: pd.DataFrame) -> pd.Series:
    """liquidity_momentum_deviation"""
    def cal(g) -> pd.Series:
        mean = ((np.log(g["close"] / g["open"])) * g["amount"]).median()
        up_power = ((np.log(g["close"] / g["open"])) * g["amount"] - mean) ** 2
        return up_power
    
    factor = df.groupby("date").apply(cal)
    factor.index = factor.index.droplevel(0)
    return factor

factor = engine.compute_one(df, "liquidity_momentum_deviation")
```

### 因子评价

```python
from evaluation.engine import EvaluatorEngine

evaluator_engine = EvaluatorEngine()

# 多周期评价
reports = evaluator_engine.evaluate_multi_horizons(
    df=df,
    factor=factor,
    horizons=[1, 5, 10],
    evaluator="common_eval"
)

# 查看评价结果
for horizon, report in reports.items():
    print(f"\n{'='*50}")
    print(f"持有期: {horizon} 天")
    print(f"{'='*50}")
    
    metrics = report.metrics
    print(f"Rank IC 均值: {metrics['rank_ic_mean']:.4f}")
    print(f"Rank IC 标准差: {metrics['rank_ic_std']:.4f}")
    print(f"Rank ICIR: {metrics['rank_ic_ir']:.4f}")
    print(f"Rank IC t 值: {metrics['rank_ic_t']:.2f}")
    print(f"多空收益均值: {metrics['group_ls_mean']:.4f}")
    print(f"Top 20% 换手率: {metrics['top_turnover_20_mean']:.4f}")
    print(f"收益单调性: {metrics['monotonic_mean']:.4f}")
    
    # 绘制评价图表
    report.plot_artifacts(show_fig=True)
```

## 🔨 扩展开发

### 自定义数据源

```python
from data_manager.interfaces import IDataSource
import pandas as pd

class MyCustomDataSource(IDataSource):
    def __init__(self, **config):
        self.config = config
    
    def load_data(self, start=None, end=None, fields=None, codes=None) -> pd.DataFrame:
        # 实现你的数据加载逻辑
        # 返回 MultiIndex(date, code) 的 DataFrame
        pass
```

### 自定义评价器

```python
from evaluation.interfaces import IEvaluator, EvalResult
from evaluation.registry import add_evaluator
import pandas as pd

class MyCustomEvaluator(IEvaluator):
    @property
    def name(self) -> str:
        return "my_evaluator"
    
    @property
    def default_params(self):
        return {"param1": 10}
    
    def evaluate(self, factor: pd.Series, ret: pd.Series, **params) -> EvalResult:
        # 实现你的评价逻辑
        metrics = {
            "metric1": 0.0,
            "metric2": 0.0,
        }
        
        artifacts = {
            "data1": pd.Series(),
        }
        
        return EvalResult(
            evaluator_name=self.name,
            factor_name=factor.name,
            metrics=metrics,
            artifacts=artifacts
        )

# 注册评价器
add_evaluator(MyCustomEvaluator())
```

## 📦 依赖项

- **Python**: 3.8+
- **pandas**: 数据处理
- **numpy**: 数值计算
- **scipy**: 统计分析
- **matplotlib**: 可视化

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

**作者**: xb1002  
**项目**: FactorFrameworkV2  
**更新日期**: 2025年11月25日