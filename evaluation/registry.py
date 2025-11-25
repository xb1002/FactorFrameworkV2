# evaluation/registry.py
from __future__ import annotations

from typing import Any, Callable, Dict, Optional, List
import pandas as pd

from .interfaces import IEvaluator, EvalResult


_EVAL_REGISTRY: Dict[str, IEvaluator] = {}


class FunctionEvaluator(IEvaluator):
    """
    把函数包装成 IEvaluator（非 dataclass）
    """
    def __init__(self, name: str, func: Callable[..., EvalResult], default_params=None):
        self._name = name
        self._func = func
        self._default_params = default_params or {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def default_params(self):
        return self._default_params

    def evaluate(self, factor: pd.Series, ret: pd.Series, **params: Any) -> EvalResult:
        p = dict(self._default_params)
        p.update(params)
        return self._func(factor, ret, **p)


def register_evaluator(
    name: Optional[str] = None,
    default_params: Optional[Dict[str, Any]] = None,
):
    """
    装饰器：注册函数式 evaluator
    """
    def deco(func: Callable[..., EvalResult]):
        ev = FunctionEvaluator(name or func.__name__, func, default_params)
        add_evaluator(ev)
        return func
    return deco


def add_evaluator(evaluator: IEvaluator):
    """
    注册类式 evaluator 实例
    """
    if evaluator.name in _EVAL_REGISTRY:
        raise KeyError(f"Evaluator '{evaluator.name}' already registered.")
    _EVAL_REGISTRY[evaluator.name] = evaluator


def get_evaluator(name: str) -> IEvaluator:
    """获取已注册的evaluator"""
    if name not in _EVAL_REGISTRY:
        available = list(_EVAL_REGISTRY.keys())
        raise KeyError(
            f"Evaluator '{name}' not registered. "
            f"Available evaluators: {available}"
        )
    return _EVAL_REGISTRY[name]


def list_evaluators() -> List[IEvaluator]:
    """列出所有已注册的 evaluator"""
    return list(_EVAL_REGISTRY.values())