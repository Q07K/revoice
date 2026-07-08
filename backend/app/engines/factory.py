from dataclasses import dataclass
from functools import lru_cache

from app.core.config import Settings, get_settings
from app.engines.applio import ApplioConverter, ApplioTrainer, CliVocalSeparator, FfmpegMixer
from app.engines.base import AudioMixer, VocalSeparator, VoiceConverter, VoiceTrainer
from app.engines.mock import MockConverter, MockMixer, MockSeparator, MockTrainer


@dataclass(frozen=True)
class EngineSet:
    trainer: VoiceTrainer
    converter: VoiceConverter
    separator: VocalSeparator
    mixer: AudioMixer


def _build_engine_set(settings: Settings) -> EngineSet:
    if settings.engine == "applio":
        return EngineSet(
            trainer=ApplioTrainer(
                settings.applio_dir, settings.applio_python, settings.training_batch_size
            ),
            converter=ApplioConverter(settings.applio_dir, settings.applio_python),
            separator=CliVocalSeparator(settings.separator_bin, settings.separator_model),
            mixer=FfmpegMixer(),
        )
    return EngineSet(
        trainer=MockTrainer(),
        converter=MockConverter(),
        separator=MockSeparator(),
        mixer=MockMixer(),
    )


@lru_cache
def get_engine_set() -> EngineSet:
    return _build_engine_set(get_settings())
