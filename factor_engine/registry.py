# factor_engine/registry.py
from __future__ import annotations
from typing import Dict, Optional, Callable, Any, List, Iterable
import pandas as pd
from .interfaces import FactorSpec

_FACTOR_REGISTRY: Dict[str, FactorSpec] = {}

def register_factor(
    name: Optional[str] = None,
    required_fields: Optional[List[str]] = None,
    params: Optional[Dict[str, Any]] = None,
    version: str = "v1",
):
    """
    装饰器：把函数注册为因子
    """
    def deco(func: Callable[..., pd.Series]):
        spec = FactorSpec(
            name=name or func.__name__,
            func=func,
            required_fields=required_fields or [],
            params=params or {},
            version=version,
        )
        if spec.name in _FACTOR_REGISTRY:
            raise KeyError(f"Factor '{spec.name}' already registered.")
        _FACTOR_REGISTRY[spec.name] = spec
        return func
    return deco

def get_factor(name: str) -> FactorSpec:
    return _FACTOR_REGISTRY[name]

def list_factors() -> Iterable[FactorSpec]:
    return _FACTOR_REGISTRY.values()
