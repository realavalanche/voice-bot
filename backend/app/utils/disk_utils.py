import shutil
from pathlib import Path


def get_disk_info(path: str) -> dict:
    """Return disk usage stats for given path, falling back to cwd if path missing."""
    check_path = path if Path(path).exists() else "."
    usage = shutil.disk_usage(check_path)
    return {
        "path": path,
        "used_gb": round(usage.used / 1e9, 3),
        "total_gb": round(usage.total / 1e9, 3),
        "percent": round(usage.used / usage.total * 100, 1),
    }
