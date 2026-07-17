from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = BASE_DIR / "data"


@dataclass(slots=True)
class AppPaths:
    data_dir: Path
    database_path: Path
    artifacts_path: Path


def get_app_paths() -> AppPaths:
    data_dir = Path(os.getenv("TRI9T_DATA_DIR", DEFAULT_DATA_DIR))
    data_dir.mkdir(parents=True, exist_ok=True)
    database_path = Path(os.getenv("TRI9T_DATABASE_PATH", data_dir / "tri9t_pipeline.db"))
    artifacts_path = Path(os.getenv("TRI9T_ARTIFACTS_PATH", data_dir / "generated_test_cases.json"))
    return AppPaths(data_dir=data_dir, database_path=database_path, artifacts_path=artifacts_path)
