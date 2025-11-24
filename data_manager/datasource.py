import pandas as pd
from data_manager.interfaces import IDataSource
from pathlib import Path


class LoacalDatasource(IDataSource):
    def __init__(self, file_path: str | Path):
        """本地数据源初始化，指定本地文件路径。
        Args:
            file_path (str | Path): 本地文件路径
        """
        self.file_path = Path(file_path)

    def load_data(self, start=None, end=None, fields=None, codes=None) -> pd.DataFrame:
        """从本地文件加载数据
        Args:
            start (Optional[pd.Timestamp], optional): 开始时间. Defaults to None.
            end (Optional[pd.Timestamp], optional): 结束时间. Defaults to None.
            fields (Optional[list[str]], optional): 需要加载的字段列表. Defaults to None.
            codes (Optional[list[str]], optional): 需要加载的标的列表. Defaults to None.
        Returns:
            pd.DataFrame: MultiIndex(date, code) 的基础数据
        """
        df = self._load_file()

        if start is not None:
            df = df[df.index.get_level_values('date') >= pd.Timestamp(start)]
        if end is not None:
            df = df[df.index.get_level_values('date') <= pd.Timestamp(end)]
        if codes is not None:
            df = df[df.index.get_level_values('code').isin(codes)]
        if fields is not None:
            if not set(fields).issubset(set(df.columns)):
                missing_fields = set(fields) - set(df.columns)
                raise ValueError(f"请求的字段不存在: {missing_fields}")
            df = df[fields]

        return df

    def _load_file(self) -> pd.DataFrame:
        """加载本地文件数据
        Returns:
            pd.DataFrame: MultiIndex(date, code) 的基础数据
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"文件未找到: {self.file_path}")

        # csv, parquet 等格式的自动识别和加载
        if self.file_path.suffix == ".csv":
            df = pd.read_csv(self.file_path, parse_dates=['date'])
        elif self.file_path.suffix == ".parquet":
            df = pd.read_parquet(self.file_path)
        else:
            raise ValueError(f"不支持的文件格式: {self.file_path.suffix}")
        
        df.set_index(['date', 'code'], inplace=True)
        df.sort_index(inplace=True)
        return df