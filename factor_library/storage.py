# factor_library/storage.py
from pathlib import Path
from typing import Dict, List, Optional
import json
import pickle
from .interfaces import FactorEntry, SourceType
from factor_engine.registry import FactorSpec


class FactorStore:
    """
    因子库的简单存储实现：
    - 负责把 FactorEntry 保存/加载到本地文件系统
    - 使用 JSON 保存元数据，使用 pickle 保存函数对象
    - 目录结构：base_dir/{factor_name}_{version}/
        - meta.json: 元数据（name, version, description, tags, metrics等）
        - func.pkl: 因子函数对象（pickle序列化）
    """
    def __init__(self, base_dir: Path, source_type: SourceType):
        self.base_dir = Path(base_dir)
        self.source_type = source_type  # 'manual' or 'auto'
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_entry_dir(self, name: str, version: str = "v1") -> Path:
        """获取因子条目的存储目录"""
        return self.base_dir / f"{name}_{version}"
    
    def _get_meta_path(self, name: str, version: str = "v1") -> Path:
        """获取元数据文件路径"""
        return self._get_entry_dir(name, version) / "meta.json"
    
    def _get_func_path(self, name: str, version: str = "v1") -> Path:
        """获取函数文件路径"""
        return self._get_entry_dir(name, version) / "func.pkl"
    
    def save_entry(self, entry: FactorEntry) -> None:
        """保存/更新一条因子记录"""
        name = entry.spec.name
        version = entry.spec.version or "v1"
        
        # 创建存储目录
        entry_dir = self._get_entry_dir(name, version)
        entry_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. 保存元数据（JSON）
        meta_data = {
            "name": name,
            "version": version,
            "source_type": entry.source_type,
            "description": entry.description,
            "tags": entry.tags,
            "last_eval_metrics": entry.last_eval_metrics,
            "required_fields": entry.spec.required_fields,
            "params": entry.spec.params,
        }
        
        meta_path = self._get_meta_path(name, version)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, indent=2, ensure_ascii=False)
        
        # 2. 保存函数对象（pickle）
        func_path = self._get_func_path(name, version)
        with open(func_path, "wb") as f:
            pickle.dump(entry.spec.func, f)

    def load_entry(self, name: str, version: Optional[str] = None) -> Optional[FactorEntry]:
        """根据因子名 + 版本号加载记录"""
        version = version or "v1"
        
        meta_path = self._get_meta_path(name, version)
        func_path = self._get_func_path(name, version)
        
        # 检查文件是否存在
        if not meta_path.exists() or not func_path.exists():
            return None
        
        try:
            # 1. 加载元数据
            with open(meta_path, "r", encoding="utf-8") as f:
                meta_data = json.load(f)
            
            # 2. 加载函数对象
            with open(func_path, "rb") as f:
                func = pickle.load(f)
            
            # 3. 重建 FactorSpec
            spec = FactorSpec(
                name=meta_data["name"],
                func=func,
                required_fields=meta_data.get("required_fields", []),
                params=meta_data.get("params", {}),
                version=meta_data.get("version", "v1"),
            )
            
            # 4. 重建 FactorEntry
            entry = FactorEntry(
                spec=spec,
                source_type=meta_data.get("source_type", self.source_type),
                description=meta_data.get("description", ""),
                tags=meta_data.get("tags", []),
                last_eval_metrics=meta_data.get("last_eval_metrics", {}),
            )
            
            return entry
            
        except Exception as e:
            print(f"Failed to load entry {name}_{version}: {e}")
            return None

    def list_entries(self) -> List[FactorEntry]:
        """列出当前仓库的所有因子记录"""
        entries: List[FactorEntry] = []
        
        if not self.base_dir.exists():
            return entries
        
        # 遍历所有因子目录
        for entry_dir in self.base_dir.iterdir():
            if not entry_dir.is_dir():
                continue
            
            # 解析目录名：factor_name_version
            parts = entry_dir.name.rsplit("_", 1)
            if len(parts) != 2:
                continue
            
            name, version = parts
            entry = self.load_entry(name, version)
            if entry is not None:
                entries.append(entry)
        
        return entries

    def delete_entry(self, name: str, version: Optional[str] = None) -> None:
        """删除指定因子记录（可选功能）"""
        version = version or "v1"
        entry_dir = self._get_entry_dir(name, version)
        
        if entry_dir.exists():
            import shutil
            shutil.rmtree(entry_dir)
    
    def exists(self, name: str, version: Optional[str] = None) -> bool:
        """检查因子是否存在"""
        version = version or "v1"
        meta_path = self._get_meta_path(name, version)
        return meta_path.exists()