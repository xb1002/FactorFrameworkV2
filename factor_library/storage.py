# factor_library/storage.py
from pathlib import Path
from typing import Dict, List, Optional
from .interfaces import FactorEntry, SourceType

class FactorStore:
    """
    因子库的简单存储抽象：
    - 负责把 FactorEntry 保存/加载到某个目录（文件、数据库等）
    - 这里只设计接口，不写实现细节
    """
    def __init__(self, base_dir: Path, source_type: SourceType):
        self.base_dir = base_dir        # 比如 ./factor_store/manual 或 ./factor_store/auto
        self.source_type = source_type  # 'manual' or 'auto'
    
    # 设计要点：只提供最小够用的接口（KISS）
    def save_entry(self, entry: FactorEntry) -> None:
        """保存/更新一条因子记录"""
        ...

    def load_entry(self, name: str, version: Optional[str] = None) -> Optional[FactorEntry]:
        """根据因子名 + 版本号加载记录"""
        ...

    def list_entries(self) -> List[FactorEntry]:
        """列出当前仓库的所有因子记录"""
        ...

    def delete_entry(self, name: str, version: Optional[str] = None) -> None:
        """删除指定因子记录（可选功能）"""
        ...