from dataclasses import dataclass
from functools import lru_cache

from app.core.config import Settings, get_settings
from app.engines.applio import (
    ApplioConverter,
    ApplioPitchAnalyzer,
    ApplioTrainer,
    CliDereverber,
    CliKaraokeSplitter,
    CliVocalSeparator,
    FfmpegMixer,
)
from app.engines.base import (
    AudioMixer,
    Dereverber,
    KaraokeSplitter,
    PitchAnalyzer,
    VideoRenderer,
    VocalSeparator,
    VoiceConverter,
    VoiceTrainer,
)
from app.engines.mock import (
    MockConverter,
    MockDereverber,
    MockKaraokeSplitter,
    MockMixer,
    MockPitchAnalyzer,
    MockSeparator,
    MockTrainer,
    MockVideoRenderer,
)
from app.engines.video import FfmpegVideoRenderer


@dataclass(frozen=True)
class EngineSet:
    trainer: VoiceTrainer
    converter: VoiceConverter
    separator: VocalSeparator
    # None disables the de-reverb pass (REVOICE_DEREVERB_MODEL="").
    dereverber: Dereverber | None
    # None disables lead/backing splitting (REVOICE_KARAOKE_MODEL="").
    karaoke: KaraokeSplitter | None
    mixer: AudioMixer
    pitch_analyzer: PitchAnalyzer
    video_renderer: VideoRenderer


def _build_engine_set(settings: Settings) -> EngineSet:
    if settings.engine == "applio":
        return EngineSet(
            trainer=ApplioTrainer(
                settings.applio_dir,
                settings.applio_python,
                settings.training_batch_size,
                settings.gpu_device,
                pretrained_g=settings.training_pretrained_g,
                pretrained_d=settings.training_pretrained_d,
                overtraining_threshold=settings.training_overtraining_threshold,
            ),
            converter=ApplioConverter(
                settings.applio_dir,
                settings.applio_python,
                split_audio=settings.conversion_split_audio,
                clean_strength=settings.conversion_clean_strength,
                reverb=settings.conversion_reverb and bool(settings.dereverb_model),
            ),
            separator=CliVocalSeparator(settings.separator_bin, settings.separator_model),
            dereverber=(
                CliDereverber(settings.separator_bin, settings.dereverb_model)
                if settings.dereverb_model
                else None
            ),
            karaoke=(
                CliKaraokeSplitter(settings.separator_bin, settings.karaoke_model)
                if settings.karaoke_model
                else None
            ),
            mixer=FfmpegMixer(),
            pitch_analyzer=ApplioPitchAnalyzer(settings.applio_python),
            video_renderer=FfmpegVideoRenderer(),
        )
    return EngineSet(
        trainer=MockTrainer(),
        converter=MockConverter(),
        separator=MockSeparator(),
        dereverber=MockDereverber(),
        karaoke=MockKaraokeSplitter(),
        mixer=MockMixer(),
        pitch_analyzer=MockPitchAnalyzer(),
        video_renderer=MockVideoRenderer(),
    )


@lru_cache
def get_engine_set() -> EngineSet:
    return _build_engine_set(get_settings())
