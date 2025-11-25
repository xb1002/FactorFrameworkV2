# factor_library/instance.py
"""
因子库全局实例管理

提供统一的因子库实例，用于外部调用
"""

from pathlib import Path
from typing import Optional, Dict, Any
import yaml

from factor_engine.engine import FactorEngine
from evaluation.engine import EvaluatorEngine

from .storage import FactorStore
from .admission import AdmissionRule
from .service import FactorLibrary


class FactorLibraryManager:
    """
    因子库管理器
    
    负责：
    1. 加载配置文件
    2. 初始化因子库实例
    3. 提供单例访问
    """
    
    _instance: Optional[FactorLibrary] = None
    _config: Optional[Dict[str, Any]] = None
    
    @classmethod
    def load_config(cls, config_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径，默认为 factor_library/config.yaml
            
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
    def initialize(
        cls,
        config_path: Optional[Path] = None,
        force_reload: bool = False
    ) -> FactorLibrary:
        """
        初始化因子库实例
        
        Args:
            config_path: 配置文件路径
            force_reload: 是否强制重新加载
            
        Returns:
            因子库实例
        """
        if cls._instance is not None and not force_reload:
            return cls._instance
        
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
            min_rank_ic_ir=admission_config.get("min_rank_ic_ir", 0.5)
        )
        
        # 创建引擎实例
        factor_engine = FactorEngine()
        evaluator_engine = EvaluatorEngine()
        
        # 创建因子库实例
        cls._instance = FactorLibrary(
            manual_store=manual_store,
            auto_store=auto_store,
            factor_engine=factor_engine,
            evaluator_engine=evaluator_engine,
            admission_rule=admission_rule,
        )
        
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> FactorLibrary:
        """
        获取因子库实例（单例模式）
        
        如果实例不存在，则自动初始化
        
        Returns:
            因子库实例
        """
        if cls._instance is None:
            cls.initialize()
        return cls._instance  # type: ignore
    
    @classmethod
    def reset(cls):
        """重置实例（主要用于测试）"""
        cls._instance = None
        cls._config = None


# 提供便捷的全局访问函数
def get_factor_library(
    config_path: Optional[Path] = None,
    force_reload: bool = False
) -> FactorLibrary:
    """
    获取因子库实例
    
    Args:
        config_path: 配置文件路径（仅首次初始化时有效）
        force_reload: 是否强制重新加载
        
    Returns:
        因子库实例
        
    Examples:
        >>> from factor_library import get_factor_library
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
    return FactorLibraryManager.initialize(config_path, force_reload)


def get_config() -> Dict[str, Any]:
    """
    获取因子库配置
    
    Returns:
        配置字典
    """
    return FactorLibraryManager.get_config()
