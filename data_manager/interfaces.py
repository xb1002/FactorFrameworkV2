from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional

class IDataSource(ABC):
    """数据源接口类"""
    @abstractmethod
    def load_data(self, start: Optional[pd.Timestamp] = None,
                  end: Optional[pd.Timestamp] = None,
                  fields: Optional[list[str]] = None,
                  codes: Optional[list[str]] = None) -> pd.DataFrame:
        """返回 MultiIndex(date, code) 的基础数据
        Args:
            start (Optional[pd.Timestamp], optional): 开始时间. Defaults to None.
            end (Optional[pd.Timestamp], optional): 结束时间. Defaults to None.
            fields (Optional[list[str]], optional): 需要加载的字段列表. Defaults to None.
            codes (Optional[list[str]], optional): 需要加载的标的列表. Defaults to None.
        Returns:
            pd.DataFrame: MultiIndex(date, code) 的基础数据
        """