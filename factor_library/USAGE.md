# 因子库使用指南

## 快速开始

### 方式1：使用全局单例（推荐）

```python
from factor_library import get_factor_library
from factor_engine.registry import FactorSpec
import pandas as pd

# 获取因子库实例（使用默认配置）
lib = get_factor_library()

# 定义因子函数
def momentum_5d(df: pd.DataFrame) -> pd.Series:
    return df.groupby(level=1)["close"].pct_change(5)

# 创建因子规格
spec = FactorSpec(
    name="momentum_5d",
    func=momentum_5d,
    required_fields=["close"],
    version="v1"
)

# 手动入库
lib.manual_admit(
    spec=spec,
    description="5日动量因子",
    tags=["momentum", "short_term"]
)

# 计算因子
factor = lib.compute_factor(df, name="momentum_5d")

# 获取评价报告
reports = lib.get_factor_report(
    df=df,
    name="momentum_5d",
    horizons=[1, 5, 10]
)
```

### 方式2：使用自定义配置

```python
from pathlib import Path
from factor_library import get_factor_library

# 使用自定义配置文件
lib = get_factor_library(config_path=Path("./my_config.yaml"))

# 其他操作同上...
```

### 方式3：手动创建实例

```python
from pathlib import Path
from factor_library import FactorLibrary, FactorStore, AdmissionRule
from factor_engine.engine import FactorEngine
from evaluation.engine import EvaluatorEngine

# 完全自定义配置
lib = FactorLibrary(
    manual_store=FactorStore(Path("./my_store/manual"), "manual"),
    auto_store=FactorStore(Path("./my_store/auto"), "auto"),
    factor_engine=FactorEngine(),
    evaluator_engine=EvaluatorEngine(),
    admission_rule=AdmissionRule(min_rank_ic=0.03, min_rank_ic_ir=0.6),
)

# 其他操作同上...
```

## 配置文件说明

配置文件 `config.yaml` 包含以下配置项：

### 存储配置
```yaml
storage:
  base_dir: "./factor_store"  # 存储根目录
  manual_dir: "manual"         # 手动入库子目录
  auto_dir: "auto"             # 自动入库子目录
```

### 入库规则配置
```yaml
admission:
  min_rank_ic: 0.02      # 最小 Rank IC 均值阈值
  min_rank_ic_ir: 0.5    # 最小 Rank IC IR 阈值
```

### 引擎配置
```yaml
engine:
  enable_cache: false    # 是否启用缓存
  cache_size: 100        # 缓存大小
```

### 评价配置
```yaml
evaluation:
  default_evaluator: "common_eval"    # 默认评价器
  default_horizons: [1, 5, 10, 20]    # 默认评价周期
  price_col: "close"                   # 价格列名
  return_kind: "simple"                # 收益率计算方式
```

## 完整示例

```python
from factor_library import get_factor_library, get_config
from factor_engine.registry import FactorSpec
import pandas as pd

# 1. 查看配置
config = get_config()
print("存储目录:", config["storage"]["base_dir"])
print("入库规则:", config["admission"])

# 2. 获取因子库实例
lib = get_factor_library()

# 3. 准备数据
dates = pd.date_range("2023-01-01", periods=100)
codes = [f"stock_{i:03d}" for i in range(50)]
index = pd.MultiIndex.from_product([dates, codes], names=["date", "code"])
df = pd.DataFrame({
    "close": 100 + pd.Series(range(len(index))) * 0.1,
}, index=index)

# 4. 定义并入库因子
def my_factor(df: pd.DataFrame) -> pd.Series:
    return df.groupby(level=1)["close"].pct_change(10)

spec = FactorSpec(
    name="my_factor",
    func=my_factor,
    required_fields=["close"],
    version="v1"
)

lib.manual_admit(spec=spec, description="我的因子", tags=["custom"])

# 5. 计算因子
factor = lib.compute_factor(df, name="my_factor")
print(factor.head())

# 6. 评价因子（可选）
# reports = lib.get_factor_report(df, name="my_factor", horizons=[1, 5, 10])
# for horizon, report in reports.items():
#     print(f"周期 {horizon}: IC={report.metrics['rank_ic_mean']:.4f}")

# 7. 列出所有因子
manual_entries = lib.manual_store.list_entries()
print(f"\n手动入库因子: {len(manual_entries)} 个")
for entry in manual_entries:
    print(f"  - {entry.spec.name} ({entry.spec.version}): {entry.description}")
```

## 最佳实践

1. **使用全局单例**: 在应用中使用 `get_factor_library()` 获取统一的实例
2. **配置管理**: 将 `config.yaml` 放在项目根目录，便于管理
3. **环境隔离**: 不同环境使用不同的配置文件（如 `config_dev.yaml`, `config_prod.yaml`）
4. **定期清理**: 删除不需要的因子，保持因子库整洁
5. **版本管理**: 使用语义化版本号管理因子版本

## 注意事项

1. `config.yaml` 文件需要安装 `pyyaml` 包：`pip install pyyaml`
2. 首次使用会自动创建存储目录
3. 全局单例在整个应用生命周期中保持唯一
4. 使用 `force_reload=True` 可以重新加载配置
