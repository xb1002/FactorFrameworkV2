"""
应用级配置和依赖注入

负责：
1. 加载配置文件
2. 初始化因子库实例
3. 提供全局访问接口
"""

from pathlib import Path
from typing import Optional, Dict, Any
import yaml

from factor_engine.engine import FactorEngine
from evaluation.engine import EvaluatorEngine
from factor_library import FactorLibrary, FactorStore, AdmissionRule


class AppConfig:
    """应用配置管理"""
    
    _config: Optional[Dict[str, Any]] = None
    _factor_lib_instance: Optional[FactorLibrary] = None
    
    @classmethod
    def load_config(cls, config_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径，默认为根目录的 config.yaml
            
        Returns:
            配置字典
        """
        if config_path is None:
            # 默认配置文件路径
            config_path = Path(__file__).parent / "config.yaml"
        
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        cls._config = config
        return config
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """
        获取配置
        
        Returns:
            配置字典
        """
        if cls._config is None:
            cls.load_config()
        return cls._config  # type: ignore
    
    @classmethod
    def create_factor_library(
        cls,
        config_path: Optional[Path] = None,
        force_reload: bool = False
    ) -> FactorLibrary:
        """
        创建因子库实例
        
        Args:
            config_path: 配置文件路径
            force_reload: 是否强制重新创建
            
        Returns:
            因子库实例
        """
        if cls._factor_lib_instance is not None and not force_reload:
            return cls._factor_lib_instance
        
        # 加载配置
        config = cls.load_config(config_path)
        
        # 解析存储配置
        storage_config = config.get("storage", {})
        base_dir = Path(storage_config.get("base_dir", "./factor_store"))
        manual_dir = storage_config.get("manual_dir", "manual")
        auto_dir = storage_config.get("auto_dir", "auto")
        
        # 创建存储实例
        manual_store = FactorStore(
            base_dir=base_dir / manual_dir,
            source_type="manual"
        )
        auto_store = FactorStore(
            base_dir=base_dir / auto_dir,
            source_type="auto"
        )
        
        # 解析入库规则配置
        admission_config = config.get("admission", {})
        admission_rule = AdmissionRule(
            min_rank_ic=admission_config.get("min_rank_ic", 0.02),
            min_rank_ic_ir=admission_config.get("min_rank_ic_ir", 0.4),
            max_top_turnover_20_mean=admission_config.get("max_top_turnover_20_mean", 0.6),
            min_monotonic_mean=admission_config.get("min_monotonic_mean", 0.1),
        )
        
        # 创建引擎实例
        factor_engine = FactorEngine()
        evaluator_engine = EvaluatorEngine()
        
        # 创建因子库实例
        cls._factor_lib_instance = FactorLibrary(
            manual_store=manual_store,
            auto_store=auto_store,
            factor_engine=factor_engine,
            evaluator_engine=evaluator_engine,
            admission_rule=admission_rule,
        )
        
        return cls._factor_lib_instance
    
    @classmethod
    def reset(cls):
        """重置实例（主要用于测试）"""
        cls._factor_lib_instance = None
        cls._config = None


# 便捷的全局访问函数
def get_factor_library(
    config_path: Optional[Path] = None,
    force_reload: bool = False
) -> FactorLibrary:
    """
    获取因子库实例（单例模式）
    
    Args:
        config_path: 配置文件路径（仅首次初始化时有效）
        force_reload: 是否强制重新加载
        
    Returns:
        因子库实例
        
    Examples:
        >>> from app import get_factor_library
        >>> 
        >>> # 使用默认配置
        >>> lib = get_factor_library()
        >>> 
        >>> # 使用自定义配置
        >>> lib = get_factor_library("./my_config.yaml")
        >>> 
        >>> # 强制重新加载
        >>> lib = get_factor_library(force_reload=True)
    """
    return AppConfig.create_factor_library(config_path, force_reload)


def get_config() -> Dict[str, Any]:
    """
    获取应用配置
    
    Returns:
        配置字典
    """
    return AppConfig.get_config()
