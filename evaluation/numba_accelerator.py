"""
Numba 加速模块

使用 numba JIT 编译优化性能瓶颈函数
"""

import numpy as np
from numba import jit, prange


@jit(nopython=True, parallel=True)
def compute_rank_ic_by_date(
    factor_values: np.ndarray,
    returns: np.ndarray,
    date_indices: np.ndarray,
    n_dates: int
) -> np.ndarray:
    """
    按日期计算 Rank IC (Spearman correlation)
    
    Args:
        factor_values: 因子值数组
        returns: 收益率数组
        date_indices: 日期索引数组
        n_dates: 日期数量
        
    Returns:
        每日 Rank IC 数组
    """
    ic_array = np.full(n_dates, np.nan, dtype=np.float64)
    
    for date_idx in prange(n_dates):
        # 找到该日期的所有数据点
        mask = date_indices == date_idx
        count = np.sum(mask)
        
        if count < 2:
            continue
        
        # 提取该日期的数据
        date_factors = factor_values[mask]
        date_returns = returns[mask]
        
        # 移除 NaN
        valid_mask = ~(np.isnan(date_factors) | np.isnan(date_returns))
        valid_count = np.sum(valid_mask)
        
        if valid_count < 2:
            continue
        
        valid_factors = date_factors[valid_mask]
        valid_returns = date_returns[valid_mask]
        
        # 检查标准差
        if np.std(valid_factors) == 0 or np.std(valid_returns) == 0:
            continue
        
        # 计算排名 (argsort 两次得到排名)
        factor_rank = np.argsort(np.argsort(valid_factors)).astype(np.float64)
        return_rank = np.argsort(np.argsort(valid_returns)).astype(np.float64)
        
        # 计算 Pearson 相关系数 (对排名)
        factor_mean = np.mean(factor_rank)
        return_mean = np.mean(return_rank)
        
        numerator = np.sum((factor_rank - factor_mean) * (return_rank - return_mean))
        denominator = np.sqrt(
            np.sum((factor_rank - factor_mean) ** 2) * 
            np.sum((return_rank - return_mean) ** 2)
        )
        
        if denominator > 0:
            ic_array[date_idx] = numerator / denominator
    
    return ic_array


@jit(nopython=True)
def compute_quantile_labels(values: np.ndarray, n_quantiles: int) -> np.ndarray:
    """
    计算分位数标签
    
    Args:
        values: 值数组
        n_quantiles: 分组数量
        
    Returns:
        标签数组 (0 到 n_quantiles-1)
    """
    n = len(values)
    labels = np.empty(n, dtype=np.int64)
    
    # 排序并获取索引
    sorted_indices = np.argsort(values)
    
    # 计算每组的大小
    base_size = n // n_quantiles
    remainder = n % n_quantiles
    
    # 分配标签
    pos = 0
    for q in range(n_quantiles):
        # 前 remainder 组多分配一个
        size = base_size + (1 if q < remainder else 0)
        for i in range(size):
            if pos < n:
                labels[sorted_indices[pos]] = q
                pos += 1
    
    return labels


@jit(nopython=True, parallel=True)
def compute_group_return_by_date(
    factor_values: np.ndarray,
    returns: np.ndarray,
    date_indices: np.ndarray,
    n_dates: int,
    n_quantiles: int
) -> np.ndarray:
    """
    按日期计算分组收益率
    
    Args:
        factor_values: 因子值数组
        returns: 收益率数组
        date_indices: 日期索引数组
        n_dates: 日期数量
        n_quantiles: 分组数量
        
    Returns:
        分组收益率数组 (n_dates, n_quantiles)
    """
    group_returns = np.full((n_dates, n_quantiles), np.nan, dtype=np.float64)
    
    for date_idx in prange(n_dates):
        # 找到该日期的所有数据
        mask = date_indices == date_idx
        count = np.sum(mask)
        
        if count < n_quantiles:
            continue
        
        # 提取该日期的数据
        date_factors = factor_values[mask]
        date_returns = returns[mask]
        
        # 移除 NaN
        valid_mask = ~(np.isnan(date_factors) | np.isnan(date_returns))
        valid_count = np.sum(valid_mask)
        
        if valid_count < n_quantiles:
            continue
        
        valid_factors = date_factors[valid_mask]
        valid_returns = date_returns[valid_mask]
        
        # 计算分位数标签
        labels = compute_quantile_labels(valid_factors, n_quantiles)
        
        # 按组计算均值
        for q in range(n_quantiles):
            group_mask = labels == q
            if np.sum(group_mask) > 0:
                group_returns[date_idx, q] = np.mean(valid_returns[group_mask])
    
    return group_returns


@jit(nopython=True)
def compute_spearman_correlation(x: np.ndarray, y: np.ndarray) -> float:
    """
    计算 Spearman 相关系数
    
    Args:
        x: 第一个数组
        y: 第二个数组
        
    Returns:
        Spearman 相关系数
    """
    if len(x) != len(y) or len(x) < 2:
        return np.nan
    
    # 计算排名
    x_rank = np.argsort(np.argsort(x)).astype(np.float64)
    y_rank = np.argsort(np.argsort(y)).astype(np.float64)
    
    # 计算 Pearson 相关系数 (对排名)
    x_mean = np.mean(x_rank)
    y_mean = np.mean(y_rank)
    
    numerator = np.sum((x_rank - x_mean) * (y_rank - y_mean))
    denominator = np.sqrt(
        np.sum((x_rank - x_mean) ** 2) * 
        np.sum((y_rank - y_mean) ** 2)
    )
    
    if denominator > 0:
        return numerator / denominator
    
    return np.nan
