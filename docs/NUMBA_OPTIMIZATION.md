# Numba 优化安装指南

## 安装 Numba

Numba 是一个 JIT 编译器，可以显著加速 NumPy 代码。

### Windows 安装

```bash
pip install numba
```

### 验证安装

```python
python -c "import numba; print(f'Numba version: {numba.__version__}')"
```

## 性能测试

运行性能测试脚本查看优化效果：

```bash
python test_numba_performance.py
```

## 优化效果

使用 numba 优化后，因子评价速度预计提升：

- **小数据集** (< 10万行): 2-3倍
- **中等数据集** (10-50万行): 3-5倍
- **大数据集** (> 50万行): 5-10倍

具体提升取决于：
- CPU 核心数（支持并行计算）
- 数据规模
- 因子复杂度

## 注意事项

1. **首次运行**: numba 会 JIT 编译函数，首次运行稍慢（多 1-2 秒）
2. **后续运行**: 编译后的函数会被缓存，显著加速
3. **兼容性**: 如果 numba 安装失败，代码会自动回退到 pandas 原生方法

## 禁用 Numba

如果需要禁用 numba 优化（调试时），可以设置环境变量：

```bash
# Windows PowerShell
$env:NUMBA_DISABLE_JIT=1
python auto_batch.py

# Linux/Mac
NUMBA_DISABLE_JIT=1 python auto_batch.py
```

## 优化的函数

- `compute_rank_ic_by_date`: 按日期计算 Rank IC（并行）
- `compute_group_return_by_date`: 按日期计算分组收益（并行）
- `compute_spearman_correlation`: Spearman 相关系数计算

这些函数是因子评价的性能瓶颈，优化后可显著提升整体速度。
