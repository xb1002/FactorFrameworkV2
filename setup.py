from setuptools import setup, find_packages
from pathlib import Path

# 查看当前父目录的名字
parent_dir_name = Path(__file__).resolve().parent.name

setup(
    name=parent_dir_name,
    version="0.1.0",
    author="xb1002",
    description="轻量级量化因子研究框架",
    packages=[parent_dir_name] + [f"{parent_dir_name}.{pkg}" for pkg in find_packages(exclude=["tests", "docs", "data", "factor_store", "*.ipynb"])],
    package_dir={parent_dir_name: "."},
    python_requires=">=3.8",
    install_requires=[
        "pandas>=1.3.0",
        "numpy>=1.20.0",
        "scipy>=1.7.0",
        "matplotlib>=3.4.0",
        "pyyaml>=5.4.0",
    ],
    extras_require={
        "notebook": ["ipywidgets>=7.6.0", "jupyter>=1.0.0"],
    },
)