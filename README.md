# FactorFramework - 因子挖掘与管理系统

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

一个轻量级、模块化的量化因子研究框架，专注于**因子挖掘、评价和管理**的完整工作流。

## 📋 目录

- [核心特性](#核心特性)
- [快速开始](#快速开始)
- [因子挖掘流程](#因子挖掘流程)
  - [方式一：交互式挖因子（推荐）](#方式一交互式挖因子推荐)
  - [方式二：自动批量挖因子](#方式二自动批量挖因子)
- [因子库管理](#因子库管理)
  - [查看因子库](#查看因子库)
  - [使用已入库因子](#使用已入库因子)
  - [删除因子](#删除因子)
- [配置说明](#配置说明)
- [项目结构](#项目结构)
- [依赖安装](#依赖安装)

---

## ✨ 核心特性

### 🎯 完整的因子挖掘工作流
- **交互式因子分析**：在 Jupyter Notebook 中实时编写、测试和评价因子
- **多周期评价**：支持 1日、5日、10日、20日等多个持有期的因子表现评价
- **自动化入库**：根据预设规则（IC、IR、换手率等）自动筛选优质因子入库
- **批量处理**：一键批量评价和入库多个候选因子

### 📊 丰富的评价指标
- **IC 指标**：IC 均值、标准差、IR、t 统计量
- **Rank IC 指标**：Rank IC 均值、标准差、IR、t 统计量
- **收益指标**：分组收益、多空收益、收益单调性
- **交易成本**：Top 20% 换手率分析
- **可视化图表**：IC 时序图、分组累计收益图、多空收益图等

### 🗄️ 双存储因子库
- **Manual Store**：手动精选的高质量因子，不检查评价指标
- **Auto Store**：自动筛选的因子，需满足入库规则（IC、IR 等阈值）
- **版本管理**：支持同一因子的多个版本共存

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install pandas numpy scipy matplotlib pyyaml ipywidgets
```

### 2. 准备数据

将行情数据放入 `data/` 目录，数据格式要求：
- **索引**：MultiIndex(date, code)
- **列**：至少包含 `close` 列，可选 `open`, `high`, `low`, `volume`, `amount` 等

示例数据：
```python
                        open    high     low   close    volume     amount
date       code                                                           
2020-01-01 000001.SZ  100.0  102.0    99.0   101.0  1000000.0  1.01e+08
           000002.SZ   50.0   51.0    49.5    50.5   500000.0  2.53e+07
```

### 3. 配置因子库

编辑 `config.yaml` 配置文件：

```yaml
# 存储配置
storage:
  base_dir: "./factor_store"
  manual_dir: "manual"
  auto_dir: "auto"

# 入库规则
admission:
  min_rank_ic: 0.02              # 最小 Rank IC 均值
  min_rank_ic_ir: 0.4            # 最小 Rank IC IR
  max_top_turnover_20_mean: 0.6  # 最大换手率（相对于周期）
  min_monotonic_mean: 0.1        # 最小收益单调性
```

### 4. 开始挖因子

打开 `analysis.ipynb` 开始交互式因子挖掘，或使用 `auto_batch.py` 进行批量处理。

---

## 🔍 因子挖掘流程

### 方式一：交互式挖因子（推荐）

使用 `analysis.ipynb` 进行交互式因子研究，适合快速实验和调试。

#### 步骤 1：加载数据和初始化引擎

```python
import pandas as pd
import numpy as np
from data_manager import LoacalDatasource
from factor_engine import register_factor, FactorEngine
from evaluation.engine import EvaluatorEngine

# 加载数据
datasource = LoacalDatasource(file_path="./data/daily_price.parquet")
df = datasource.load_data(start="2020-01-01", end="2026-01-01")

# 初始化引擎
factor_engine = FactorEngine()
evaluator_engine = EvaluatorEngine()
```

#### 步骤 2：定义因子

```python
factor_name = "my_momentum_factor"

@register_factor(
    name=factor_name,
    required_fields=["close"],
    version="v1"
)
def my_momentum_factor(df: pd.DataFrame) -> pd.Series:
    """
    自定义动量因子
    
    参数:
        df: MultiIndex(date, code) 的 DataFrame
        
    返回:
        pd.Series: 因子值，索引与 df 对齐
    """
    # 示例：20日收益率
    return df.groupby(level="code")["close"].pct_change(20)
```

**因子编写注意事项**：
- 输入：`df` 的索引必须是 `MultiIndex(date, code)`
- 输出：返回的 `Series` 索引必须与 `df` 对齐
- 分组计算：使用 `groupby(level="code")` 或 `groupby(level="date")`
- 避免未来函数：不要使用未来数据

#### 步骤 3：评价因子

```python
# 多周期评价
reports = evaluator_engine.evaluate_multi_horizons(
    df=df,
    factor=factor_engine.compute_one(df, factor_name),
    horizons=[1, 5, 10, 20],  # 持有期列表
    evaluator="common_eval"
)

# 查看评价结果
for horizon, report in reports.items():
    print(f"=== 持有期: {horizon} 天 ===")
    print(f"Rank IC: {report.metrics['rank_ic_mean']:.4f}")
    print(f"Rank IR: {report.metrics['rank_ic_ir']:.4f}")
    print(f"多空收益: {report.metrics['group_ls_mean']:.4f}")
    print(f"换手率: {report.metrics['top_turnover_20_mean']:.4f}")
    
    # 绘制图表
    report.plot_artifacts(show_fig=True)
```

**评价指标说明**：

| 指标 | 说明 | 好的标准 |
|------|------|----------|
| `rank_ic_mean` | Rank IC 均值 | 绝对值 > 0.02 |
| `rank_ic_ir` | Rank IC IR（信息比率） | 绝对值 > 0.4 |
| `group_ls_mean` | 多空组合收益 | 越大越好 |
| `top_turnover_20_mean` | Top 20% 换手率 | 相对于周期 < 0.6 |
| `monotonic_mean` | 收益单调性 | 绝对值 > 0.1 |

#### 步骤 4：手动入库因子

如果因子表现良好，可以手动入库：

```python
from app import get_factor_library
from factor_engine import get_factor

# 获取因子库实例
factor_lib = get_factor_library()

# 手动入库（会自动保存到 manual_store）
factor_lib.manual_admit(
    spec=get_factor(factor_name),
    description="我的动量因子 - 20日收益率",
    tags=["momentum", "medium_term", "custom"]
)

print(f"✓ 因子 '{factor_name}' 已入库到 Manual Store")
```

#### 步骤 5：交互式查看（可选）

使用 ipywidgets 交互式查看不同周期的评价结果：

```python
import json
import ipywidgets as widgets
from ipywidgets import interact
import matplotlib.pyplot as plt

def show_report(h):
    plt.close('all')
    report = reports[h]
    print(f"=== 持有期: {h} 天 ===")
    print(json.dumps(report.metrics, indent=4))
    report.plot_artifacts(show_fig=True)

interact(
    show_report,
    h=widgets.Dropdown(
        options=sorted(reports.keys()),
        description="Horizon",
    )
)
```

---

### 方式二：自动批量挖因子

使用 `auto_batch.py` 批量处理候选因子，自动评价并根据规则入库。

#### 步骤 1：定义候选因子

在 `factors/auto.py` 中定义待评价的因子：

```python
"""
自动挖掘的因子（待评价入库）
所有在这里注册的因子会被 auto_batch.py 自动评价并判断是否入库
"""

import pandas as pd
import numpy as np
from factor_engine import register_factor

@register_factor(
    name="momentum_5d",
    required_fields=["close"],
    version="v1"
)
def momentum_5d(df: pd.DataFrame) -> pd.Series:
    """5日动量因子"""
    return df.groupby(level="code")["close"].pct_change(5)

@register_factor(
    name="momentum_10d",
    required_fields=["close"],
    version="v1"
)
def momentum_10d(df: pd.DataFrame) -> pd.Series:
    """10日动量因子"""
    return df.groupby(level="code")["close"].pct_change(10)

@register_factor(
    name="volatility_20d",
    required_fields=["close"],
    version="v1"
)
def volatility_20d(df: pd.DataFrame) -> pd.Series:
    """20日波动率因子"""
    return (df.groupby(level="code")["close"]
            .pct_change()
            .rolling(20)
            .std())

# ... 添加更多因子
```

#### 步骤 2：运行自动批量入库

```bash
python auto_batch.py
```

脚本会自动：
1. 加载 `factors/auto.py` 中定义的所有因子
2. 计算每个因子的值
3. 在多个持有期（1、5、10、20日）上评价因子
4. 根据入库规则自动判断是否入库到 `auto_store`
5. 输出详细的评价报告

**运行示例输出**：

```
================================================================================
初始化自动因子处理器
================================================================================

加载数据: ./data/daily_price.parquet
✓ 数据加载完成: 150000 行
✓ 因子库初始化完成
  - 入库规则: |IC| >= 0.02, |IR| >= 0.4, 换手率/周期 <= 0.6, |单调性| >= 0.1
  - 评价周期: [1, 5, 10, 20]

找到 3 个已注册因子
  - 已入库: 0 个
  - 待处理: 3 个

################################################################################
# 进度: 1/3
################################################################################
================================================================================
处理因子: momentum_5d (v1)
================================================================================
  [1/2] 计算因子值...
        ✓ 计算完成 (非空值: 148500)
  [2/2] 评价因子表现...
        ✓ 评价完成

  [评价摘要]
    周期 |    Rank IC |     IC IR |   多空收益 |     换手率
  -----------------------------------------------------------------
     1日 |     0.0234 |     0.5234 |     0.0012 |     0.4521
     5日 |     0.0312 |     0.6123 |     0.0056 |     0.5234
    10日 |     0.0287 |     0.5876 |     0.0089 |     0.5876
    20日 |     0.0198 |     0.4234 |     0.0134 |     0.6234

  [入库判断] 检查各周期评价结果
        -  1日: Rank IC= 0.0234, IR= 0.5234, 换手率/周期= 0.4521, |单调性|= 0.2341  ✓ 通过
        
  [入库决策] 使用 1 日评价结果进行入库
        ✓ 入库成功！

...

================================================================================
处理完成
================================================================================
  - 总共处理: 3 个因子
  - 成功入库: 2 个
  - 未通过: 1 个

当前因子库统计:
  - 手动入库: 0 个
  - 自动入库: 2 个
  - 总计: 2 个
```

#### 自动入库规则

因子需要满足以下条件之一（任一周期通过即可）：

```python
# 在 config.yaml 中配置
admission:
  min_rank_ic: 0.02              # |Rank IC| >= 0.02
  min_rank_ic_ir: 0.4            # |Rank IC IR| >= 0.4
  max_top_turnover_20_mean: 0.6  # 换手率/周期 <= 0.6
  min_monotonic_mean: 0.1        # |收益单调性| >= 0.1
```

**逻辑**：
- 脚本会按从短到长的顺序检查每个周期（1日 → 5日 → 10日 → 20日）
- 找到第一个满足所有条件的周期，使用该周期的评价结果入库
- 如果所有周期都不满足条件，则不入库

---

## 📚 因子库管理

### 查看因子库

```python
from app import get_factor_library

# 获取因子库实例
lib = get_factor_library()

# 查看统计信息
stats = lib.get_factor_count()
print(f"手动入库: {stats['manual']} 个")
print(f"自动入库: {stats['auto']} 个")
print(f"总计: {stats['total']} 个")

# 列出所有手动入库因子
print("\n=== Manual Store ===")
for entry in lib.manual_store.list_entries():
    print(f"- {entry.spec.name} ({entry.spec.version})")
    print(f"  描述: {entry.description}")
    print(f"  标签: {entry.tags}")
    print(f"  时间: {entry.created_at}")
    print()

# 列出所有自动入库因子
print("=== Auto Store ===")
for entry in lib.auto_store.list_entries():
    print(f"- {entry.spec.name} ({entry.spec.version})")
    print(f"  描述: {entry.description}")
    print(f"  评价指标: Rank IC={entry.eval_metrics.get('rank_ic_mean', 0):.4f}")
    print()
```

### 使用已入库因子

```python
from app import get_factor_library
from data_manager import LoacalDatasource

# 加载数据
datasource = LoacalDatasource(file_path="./data/daily_price.parquet")
df = datasource.load_data(start="2020-01-01", end="2026-01-01")

# 获取因子库
lib = get_factor_library()

# 从因子库计算因子
factor = lib.compute_factor(
    df=df,
    name="momentum_5d",
    version="v1"
)

print(factor.head())
```

### 获取因子评价报告

```python
# 为已入库因子生成新的评价报告
reports = lib.get_factor_report(
    df=df,
    name="momentum_5d",
    horizons=[1, 5, 10, 20],
    evaluator_name="common_eval",
    version="v1"
)

# 查看报告
for horizon, report in reports.items():
    print(f"周期 {horizon}: IC={report.metrics['rank_ic_mean']:.4f}")
```

### 删除因子

```python
# 从 manual_store 删除
lib.manual_store.delete_entry(name="my_factor", version="v1")

# 从 auto_store 删除
lib.auto_store.delete_entry(name="momentum_5d", version="v1")

print("✓ 因子已删除")
```

### 批量手动入库

使用 `manual_batch.py` 批量将手动挖掘的因子入库：

```python
# 1. 在 factors/manual.py 中定义因子
# 2. 运行批量入库脚本
```

```bash
python manual_batch.py
```

---

## ⚙️ 配置说明

### config.yaml

完整的配置文件示例：

```yaml
# 存储配置
storage:
  base_dir: "./factor_store"      # 因子库根目录
  manual_dir: "manual"             # 手动入库子目录
  auto_dir: "auto"                 # 自动入库子目录

# 入库规则配置
admission:
  # 因子入库的最小 Rank IC 均值（绝对值）
  min_rank_ic: 0.02
  
  # 因子入库的最小 Rank IC IR（绝对值）
  min_rank_ic_ir: 0.4
  
  # 因子入库的最大换手率（相对于持有期）
  # 例如：周期为 5 日，换手率为 3.0，则相对换手率为 3.0/5=0.6
  max_top_turnover_20_mean: 0.6
  
  # 因子入库的最小收益单调性（绝对值）
  # 衡量因子分组收益的单调性
  min_monotonic_mean: 0.1
```

**参数调优建议**：

- **宽松规则**：降低 `min_rank_ic` 和 `min_rank_ic_ir`，放宽 `max_top_turnover_20_mean`
  - 适合：探索阶段，希望入库更多候选因子
  
- **严格规则**：提高所有阈值
  - 适合：生产环境，只保留高质量因子

### 存储目录结构

```
factor_store/
├── manual/                      # 手动入库的因子
│   └── liquidity_momentum_deviation_v1/
│       ├── meta.json           # 因子元数据
│       └── func.pkl            # 因子函数对象（pickle）
└── auto/                        # 自动入库的因子
    ├── momentum_5d_v1/
    │   ├── meta.json
    │   └── func.pkl
    └── momentum_10d_v1/
        ├── meta.json
        └── func.pkl
```

**meta.json 示例**：

```json
{
    "name": "momentum_5d",
    "version": "v1",
    "description": "5日动量因子",
    "tags": ["momentum", "short_term"],
    "source": "auto",
    "created_at": "2025-11-26T10:30:00",
    "required_fields": ["close"],
    "eval_metrics": {
        "rank_ic_mean": 0.0234,
        "rank_ic_ir": 0.5234,
        "group_ls_mean": 0.0012,
        "top_turnover_20_mean": 0.4521
    },
    "eval_horizon": 1
}
```

---

## 📁 项目结构

```
FactorFramework/
├── config.yaml                  # 配置文件
├── app.py                       # 应用入口，依赖注入
├── README.md                    # 本文档
│
├── analysis.ipynb               # 交互式因子分析（推荐）
├── manual.ipynb                 # 手动入库操作示例
├── manual_batch.py              # 批量手动入库脚本
├── auto_batch.py                # 自动批量入库脚本
│
├── data/                        # 数据目录
│   └── daily_price.parquet     # 日频行情数据
│
├── factor_store/                # 因子库存储
│   ├── manual/                 # 手动入库因子
│   └── auto/                   # 自动入库因子
│
├── factors/                     # 因子定义
│   ├── manual.py               # 手动挖掘的因子
│   └── auto.py                 # 待自动评价的因子
│
├── data_manager/                # 数据管理模块
│   ├── interfaces.py           # 数据源接口
│   └── datasource.py           # 本地数据源实现
│
├── factor_engine/               # 因子引擎模块
│   ├── interfaces.py           # 因子接口定义
│   ├── registry.py             # 因子注册表
│   └── engine.py               # 因子计算引擎
│
├── evaluation/                  # 评价引擎模块
│   ├── interfaces.py           # 评价器接口
│   ├── registry.py             # 评价器注册表
│   ├── forward_return.py       # 未来收益计算
│   ├── builtins.py             # 内置评价器
│   └── engine.py               # 评价引擎
│
└── factor_library/              # 因子库模块
    ├── interfaces.py           # 因子库接口
    ├── storage.py              # 因子存储实现
    ├── admission.py            # 入库规则
    ├── service.py              # 因子库服务
    ├── README.md               # 模块详细文档
    └── USAGE.md                # 使用指南
```

---

## 📦 依赖安装

### 必需依赖

```bash
pip install pandas numpy scipy matplotlib pyyaml
```

### 可选依赖

```bash
# 交互式 Notebook 支持
pip install ipywidgets jupyter

# 数据处理加速
pip install pyarrow fastparquet
```

### 完整安装

```bash
pip install pandas numpy scipy matplotlib pyyaml ipywidgets jupyter pyarrow
```

---

## 📖 使用案例

### 案例 1：动量因子挖掘

```python
# 在 analysis.ipynb 中

# 1. 定义因子
@register_factor(name="momentum_20d", required_fields=["close"])
def momentum_20d(df):
    return df.groupby(level="code")["close"].pct_change(20)

# 2. 评价因子
reports = evaluator_engine.evaluate_multi_horizons(
    df=df,
    factor=factor_engine.compute_one(df, "momentum_20d"),
    horizons=[1, 5, 10, 20]
)

# 3. 查看结果并决定是否入库
# 如果表现良好，手动入库
factor_lib.manual_admit(spec=get_factor("momentum_20d"))
```

### 案例 2：复合因子

```python
@register_factor(
    name="liquidity_momentum_deviation",
    required_fields=["open", "close", "amount"]
)
def liquidity_momentum_deviation(df):
    """成交额加权的动量偏离度"""
    def cal(g):
        mean = ((np.log(g["close"] / g["open"])) * g["amount"]).median()
        deviation = ((np.log(g["close"] / g["open"])) * g["amount"] - mean) ** 2
        return deviation
    
    factor = df.groupby("date").apply(cal)
    factor.index = factor.index.droplevel(0)
    return factor
```

### 案例 3：批量因子测试

```python
# 在 factors/auto.py 中定义多个因子
# 然后运行批量脚本

# Terminal:
$ python auto_batch.py

# 自动评价所有因子并根据规则入库
```

---

## 🎓 最佳实践

### 1. 因子编写规范

- **索引对齐**：确保输出 Series 的索引与输入 DataFrame 对齐
- **避免未来函数**：不要使用未来数据
- **处理缺失值**：合理处理 NaN 值
- **性能优化**：使用向量化操作，避免循环

### 2. 因子评价流程

1. **先交互式测试**：使用 `analysis.ipynb` 快速验证因子逻辑
2. **多周期评价**：至少测试 4 个不同持有期（1、5、10、20日）
3. **查看可视化**：不仅看数值指标，还要看 IC 时序图、分组收益图
4. **综合判断**：不仅看 IC/IR，还要考虑换手率、单调性、稳定性

### 3. 因子管理策略

- **Manual Store**：精选高质量因子，手动审核后入库
- **Auto Store**：批量筛选的因子，定期回顾和清理
- **版本控制**：重要修改使用新版本号，保留历史版本
- **标签分类**：使用标签组织因子，如 `["momentum", "short_term"]`

### 4. 配置调优

- **探索阶段**：使用宽松规则，入库更多候选因子
- **生产环境**：使用严格规则，只保留高质量因子
- **定期回测**：定期对已入库因子进行回测验证

---

## 🔧 常见问题

### Q1：如何处理因子计算中的异常？

```python
try:
    factor = factor_engine.compute_one(df, factor_name)
except Exception as e:
    print(f"因子计算失败: {e}")
    # 检查因子定义和数据
```

### Q2：如何自定义入库规则？

```python
from factor_library import AdmissionRule

# 创建自定义规则
custom_rule = AdmissionRule(
    min_rank_ic=0.03,        # 更严格的 IC 要求
    min_rank_ic_ir=0.6,      # 更严格的 IR 要求
    max_top_turnover_20_mean=0.5,  # 更低的换手率
    min_monotonic_mean=0.15  # 更高的单调性
)

# 使用自定义规则创建因子库
from factor_library import FactorLibrary, FactorStore
from factor_engine import FactorEngine
from evaluation import EvaluatorEngine

lib = FactorLibrary(
    manual_store=FactorStore(...),
    auto_store=FactorStore(...),
    factor_engine=FactorEngine(),
    evaluator_engine=EvaluatorEngine(),
    admission_rule=custom_rule  # 使用自定义规则
)
```

### Q3：如何批量计算多个因子？

```python
# 方法1：使用 FactorEngine
factor_dict = {}
for name in ["momentum_5d", "momentum_10d", "momentum_20d"]:
    factor_dict[name] = factor_engine.compute_one(df, name)

# 方法2：从因子库批量计算
lib = get_factor_library()
entries = lib.manual_store.list_entries()

for entry in entries:
    factor = lib.compute_factor(df, entry.spec.name, entry.spec.version)
    print(f"{entry.spec.name}: 计算完成")
```

### Q4：如何导出因子数据？

```python
# 计算因子
factor = lib.compute_factor(df, name="momentum_5d")

# 导出为 CSV
factor.to_csv("factor_momentum_5d.csv")

# 导出为 Parquet
factor.to_frame(name="factor_value").to_parquet("factor_momentum_5d.parquet")
```

---

## 📞 联系与贡献

- **作者**：xb1002
- **项目**：FactorFrameworkV2
- **分支**：dev

欢迎提交 Issue 和 Pull Request！

---

**Happy Factor Mining! 🚀**
