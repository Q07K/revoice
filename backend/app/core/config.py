from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REVOICE_", env_file=".env")

    app_name: str = "Revoice"
    database_url: str = "sqlite:///./revoice.db"
    storage_dir: Path = Path("./storage")
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # "mock" runs the whole pipeline without a GPU; "applio" shells out to a
    # local Applio checkout for real RVC training/inference.
    engine: Literal["mock", "applio"] = "mock"
    applio_dir: Path = Path("./vendor/applio")
    applio_python: str = "python"
    separator_bin: str = "audio-separator"
    separator_model: str = "model_bs_roformer_ep_317_sdr_12.9755.ckpt"
    training_sample_rate: int = 40000
    training_batch_size: int = 4
    job_workers: int = 2

    # 커버 예상 시간 계산용 배속 (오디오 1초당 처리 시간, CPU 실측 기준).
    # GPU 환경에서는 훨씬 작아지므로 .env에서 조정한다.
    separation_speed_factor: float = 3.6
    conversion_speed_factor: float = 0.7


@lru_cache
def get_settings() -> Settings:
    return Settings()
