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
    # 분리기를 상주 프로세스로 유지해 호출마다 드는 모델 로드(20~30초)를 없앤다.
    separator_daemon: bool = True
    # 상주 분리기가 쓸 파이썬. 비우면 separator_bin 옆의 python을 쓴다.
    separator_python: str = ""
    separator_model: str = "model_bs_roformer_ep_317_sdr_12.9755.ckpt"
    training_sample_rate: int = 48000
    training_batch_size: int = 8
    job_workers: int = 2

    # RVC 추론 품질: 무음 기준 분할 변환(긴 곡 품질 저하 방지)과 변환 결과의
    # 노이즈 제거 강도. clean_strength는 Applio 규약상 0.1 단위(0이면 끔).
    # 주의: clean(noisereduce)은 split_audio가 복원한 전무음 구간에서 NaN을
    # 만들고, 이어지는 리버브(IIR)가 NaN을 전곡으로 전파해 결과가 통째로
    # 무음이 된다. Applio가 고치기 전까지 기본 비활성.
    conversion_split_audio: bool = True
    conversion_clean_strength: float = 0.0

    # 학습 데이터셋 자동 정제: 학습 전에 각 파일을 보컬 분리 + 디리버브로
    # 정리한다. 일반 사용자의 업로드(BGM 깔린 녹음, 노래방 녹음)에서 모델 품질
    # 하한선을 크게 올린다.
    training_dataset_cleanup: bool = True
    # 커스텀 pretrained (G/D 경로, 둘 다 존재할 때만 적용). 커뮤니티 pretrain은
    # 적은 데이터·적은 epoch에서 기본 pretrained보다 수렴이 좋다.
    training_pretrained_g: Path | None = None
    training_pretrained_d: Path | None = None
    # N epoch 동안 개선이 없으면 조기 종료 (0이면 끔). 과적합 방지.
    training_overtraining_threshold: int = 50

    # 분리된 보컬의 리버브/에코 제거 모델 (audio-separator 모델명, 빈 문자열이면
    # 끔). 원곡 리버브가 RVC에 들어가면 뭉개짐·금속성 아티팩트가 심해진다.
    dereverb_model: str = "dereverb_mel_band_roformer_anvuew_sdr_19.1729.ckpt"
    # 리드/코러스 분리 모델 (빈 문자열이면 끔). 코러스가 겹친 보컬을 통째로
    # 변환하면 목소리가 뭉개지므로, 리드만 변환하고 코러스는 반주에 남긴다.
    karaoke_model: str = "mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt"
    # 코러스 스템 평균 레벨이 이보다 작으면 "코러스 없음"으로 보고 원 보컬을
    # 그대로 변환한다 (솔로곡에 카라오케 아티팩트를 얹지 않기 위함).
    karaoke_backing_floor_db: float = -50.0
    # 변환 보컬에 공간감을 되입히는 리버브 (Applio post_process의 pedalboard
    # Freeverb). 실청취 결과 "노래방 에코" 느낌이라 기본 꺼짐 — 드라이 보컬이
    # 더 깔끔하다는 사용자 피드백 (2026-07-14).
    conversion_reverb: bool = False

    # Applio GPU 장치 인덱스. "0"이면 첫 번째 CUDA GPU, "-"이면 CPU.
    # 여러 GPU는 "0-1"처럼 지정한다 (Applio core.py의 --gpu 규약).
    gpu_device: str = "0"

    # 커버 예상 시간 계산용 배속 (오디오 1초당 처리 시간, CPU 실측 기준).
    # GPU 환경에서는 훨씬 작아지므로 .env에서 조정한다.
    separation_speed_factor: float = 3.6
    conversion_speed_factor: float = 0.7


@lru_cache
def get_settings() -> Settings:
    return Settings()
