import sys
from pathlib import Path
# 添加项目根目录到 sys.path
project_root = Path(__file__).parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    
from .app import get_factor_library
factor_lib = get_factor_library()