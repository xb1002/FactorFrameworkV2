# 因子库组件 (Factor Library)

因子库组件是量化因子框架的核心模块之一，负责因子的存储、管理、计算和评价。

## 📋 目录结构

```
factor_library/
├── __init__.py          # 模块导出
├── interfaces.py        # 接口定义（FactorEntry, SourceType）
├── storage.py          # 存储实现（FactorStore）
├── admission.py        # 入库规则（AdmissionRule）
├── service.py          # 因子库服务（FactorLibrary）
└── README.md           # 本文档
```

## 🎯 核心功能

### 1. 因子存储 (FactorStore)

负责因子的持久化存储，使用文件系统保存因子元数据和函数对象。

**存储结构：**
```
base_dir/
└── {factor_name}_{version}/
    ├── meta.json        # 元数据（名称、版本、描述、标签等）
    └── func.pkl         # 因子函数对象（pickle序列化）
```

**主要方法：**
- `save_entry(entry)`: 保存因子条目
- `load_entry(name, version)`: 加载因子条目
- `list_entries()`: 列出所有因子
- `delete_entry(name, version)`: 删除因子
- `exists(name, version)`: 检查因子是否存在

### 2. 入库规则 (AdmissionRule)

定义自动入库的阈值标准，支持自定义规则。

**默认规则：**
- `min_rank_ic`: 最小 Rank IC 阈值（默认 0.02）
- `min_rank_ic_ir`: 最小 Rank IC IR 阈值（默认 0.4）

### 3. 因子库服务 (FactorLibrary)

对外统一的因子库服务接口，整合因子计算、评价和管理功能。

**核心方法：**

#### 入库管理
```python
# 手动入库：直接添加因子，不检查评价结果
manual_admit(spec, description, tags, eval_result)

# 自动入库：根据评价结果和规则决定是否入库
auto_admit_from_eval(spec, eval_result, description, tags)
```

#### 因子计算
```python
# 从因子库中加载并计算因子
compute_factor(df, name, version, **params)
```

#### 因子评价
```python
# 获取因子的评价报告（多周期）
get_factor_report(df, name, horizons, evaluator_name, version)
```

## 🚀 快速开始

### 基础使用

```python
from pathlib import Path
from factor_library import FactorLibrary, FactorStore, AdmissionRule
from factor_engine.engine import FactorEngine
from factor_engine.registry import FactorSpec
from evaluation.engine import EvaluatorEngine

# 1. 创建存储实例
manual_store = FactorStore(Path("./factor_store/manual"), source_type="manual")
auto_store = FactorStore(Path("./factor_store/auto"), source_type="auto")

# 2. 创建引擎
factor_engine = FactorEngine()
evaluator_engine = EvaluatorEngine()

# 3. 定义入库规则
admission_rule = AdmissionRule(
    min_rank_ic=0.02,
    min_rank_ic_ir=0.5
)

# 4. 创建因子库
factor_lib = FactorLibrary(
    manual_store=manual_store,
    auto_store=auto_store,
    factor_engine=factor_engine,
    evaluator_engine=evaluator_engine,
    admission_rule=admission_rule,
)
```

### 手动入库因子

```python
from factor_engine.registry import register_factor, FactorSpec

# 定义因子
@register_factor(name="momentum_5d", required_fields=["close"], version="v1")
def momentum_5d(df):
    return df.groupby(level=1)["close"].pct_change(5)

# 创建 FactorSpec
spec = FactorSpec(
    name="momentum_5d",
    func=momentum_5d.__wrapped__,
    required_fields=["close"],
    version="v1"
)

# 手动入库
factor_lib.manual_admit(
    spec=spec,
    description="5日动量因子",
    tags=["momentum", "short_term"],
)
```

### 自动入库（基于评价）

```python
from evaluation.interfaces import EvalResult

# 计算因子并评价
factor_values = my_factor_func(df)

# 假设已经得到评价结果
eval_result = EvalResult(
    evaluator_name="common_eval",
    factor_name="my_factor",
    metrics={
        "rank_ic_mean": 0.035,
        "rank_ic_ir": 0.65,
    }
)

# 创建 FactorSpec
spec = FactorSpec(
    name="my_factor",
    func=my_factor_func,
    required_fields=["close", "volume"],
    version="v1"
)

# 尝试自动入库（根据规则判断）
success = factor_lib.auto_admit_from_eval(
    spec=spec,
    eval_result=eval_result,
    description="我的自定义因子",
    tags=["custom"],
)

if success:
    print("因子入库成功！")
else:
    print("因子未达标，入库失败。")
```

### 计算因子

```python
import pandas as pd

# 准备数据（MultiIndex: date, code）
df = pd.DataFrame(...)

# 从因子库计算因子
factor = factor_lib.compute_factor(
    df=df,
    name="momentum_5d",
    version="v1"
)

print(factor.head())
```

### 获取因子评价报告

```python
# 获取多周期评价报告
reports = factor_lib.get_factor_report(
    df=df,
    name="momentum_5d",
    horizons=[1, 5, 10, 20],
    evaluator_name="common_eval",
    version="v1"
)

# 查看各周期的评价结果
for horizon, result in reports.items():
    print(f"\n{horizon}日评价:")
    print(f"  Rank IC: {result.metrics['rank_ic_mean']:.4f}")
    print(f"  IC IR: {result.metrics['rank_ic_ir']:.4f}")
```

## 📊 完整示例

查看 `example.py` 文件获取完整的使用示例，包括：

1. 初始化因子库组件
2. 准备模拟数据
3. 手动入库因子
4. 自动入库（基于评价）
5. 从因子库计算因子
6. 查看因子库存

运行示例：

```bash
python factor_library/example.py
```

## 🔧 设计要点

### 1. 双存储体系

- **Manual Store**: 手动入库的因子，不检查评价指标
- **Auto Store**: 自动入库的因子，需满足入库规则

### 2. 与 FactorEngine 集成

因子库不重复实现因子计算逻辑，而是复用 `FactorEngine`：
- 存储时：保存 `FactorSpec`（包含函数、参数等）
- 计算时：调用 `FactorEngine.compute_one()` 

### 3. 与 EvaluatorEngine 集成

因子库提供统一的评价接口：
- 内部调用 `compute_factor()` 计算因子
- 然后调用 `EvaluatorEngine.evaluate_multi_horizons()` 评价
- 返回 `Dict[int, EvalResult]` 供用户使用

### 4. 灵活的存储实现

- 使用 JSON 保存元数据（易读、易维护）
- 使用 pickle 保存函数对象（支持任意函数）
- 目录结构清晰，便于管理和备份

### 5. KISS 原则

- 最小化接口设计
- 关注核心功能
- 易于理解和使用

## 🔄 数据流

```
因子定义 (FactorSpec)
    ↓
手动入库 / 自动入库
    ↓
因子库存储 (FactorStore)
    ↓
加载因子 (load_entry)
    ↓
因子计算 (FactorEngine)
    ↓
因子评价 (EvaluatorEngine)
    ↓
评价报告 (EvalResult)
```

## 📝 注意事项

1. **函数序列化**：使用 pickle 序列化函数时，确保函数可被序列化（避免使用 lambda、local 函数等）

2. **版本管理**：同一因子的不同版本可以共存，通过 `version` 参数区分

3. **线程安全**：当前实现为单线程设计，多线程环境需额外加锁

4. **存储清理**：定期清理不需要的因子，避免磁盘占用过大

5. **备份策略**：因子库数据建议定期备份，防止数据丢失

## 🎓 最佳实践

1. **命名规范**：使用清晰的因子名称，如 `momentum_5d`、`volatility_20d`

2. **版本控制**：重要修改时更新版本号，保留历史版本

3. **标签管理**：合理使用标签分类因子，如 `["momentum", "short_term"]`

4. **评价先行**：新因子先评价，达标后再入库

5. **定期清理**：删除过时或低质量的因子

## 🔗 相关模块

- `factor_engine`: 因子计算引擎
- `evaluation`: 因子评价引擎
- `data_manager`: 数据源管理

## 📚 API 参考

详细 API 文档请参考各模块的 docstring。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
