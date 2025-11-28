# 导入所有手动挖的因子
import factors.manual  # noqa: F401
# 注册自定义因子
try:
    import factors.manual_factors  # noqa: F401
except ImportError:
    pass

from factor_engine import list_factors

from app import get_factor_library
factor_lib = get_factor_library()

# 批量注册因子
if __name__ == "__main__":
    all_factors = list_factors()
    for factor in all_factors:
        factor_lib.manual_admit(factor)