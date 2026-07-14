import json
import logging
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass, replace
from functools import partial
from pathlib import Path
from types import TracebackType

from fastapi import Depends, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal, get_db
from app.core.exceptions import ConflictError, NotFoundError
from app.engines.base import (
    ConversionSpec,
    EngineError,
    audio_duration_seconds,
    mean_volume_db,
    run_command,
)
from app.engines.factory import get_engine_set
from app.engines.pitch import octave_shift_semitones
from app.engines.waveform import compute_waveform_peaks
from app.features.covers import crud
from app.features.covers.models import CoverJob, CoverStatus
from app.features.voices import crud as voices_crud
from app.features.voices.models import VoiceStatus
from app.features.voices.service import validate_audio_filename
from app.jobs.runner import JobRunner, get_job_runner
from app.storage.files import FileStorage, get_file_storage

logger = logging.getLogger(__name__)

_IN_PROGRESS_STATUSES = frozenset(
    {
        CoverStatus.PENDING,
        CoverStatus.SEPARATING,
        CoverStatus.CONVERTING,
        CoverStatus.MIXING,
    }
)


class CoverService:
    def __init__(self, db: Session, storage: FileStorage, runner: JobRunner) -> None:
        self._db = db
        self._storage = storage
        self._runner = runner

    def create(
        self,
        voice_id: int,
        transpose: int,
        auto_transpose: bool,
        vocal_gain: float,
        index_rate: float,
        protect: float,
        volume_envelope: float,
        song: UploadFile,
    ) -> CoverJob:
        voice = voices_crud.get_voice(self._db, voice_id)
        if voice is None:
            raise NotFoundError(f"Voice {voice_id} not found.")
        if voice.status is not VoiceStatus.READY:
            raise ConflictError("The voice must finish training before generating covers.")
        title = validate_audio_filename(song.filename)
        song_path = self._storage.save_upload(song, self._storage.songs_dir())
        cover = crud.create_cover(
            self._db,
            voice_id,
            title,
            str(song_path),
            transpose,
            auto_transpose,
            vocal_gain,
            index_rate,
            protect,
            volume_envelope,
        )
        self._runner.submit(partial(execute_cover, cover.id))
        return cover

    def remix(self, cover_id: int, vocal_gain: float) -> CoverJob:
        """Re-mix an existing cover at a new vocal volume without re-running the
        slow separation/conversion stages (their outputs are cached per cover)."""
        cover = self.get(cover_id)
        if cover.status is not CoverStatus.COMPLETED:
            raise ConflictError("완성된 커버만 볼륨을 다시 조정할 수 있어요.")
        work_dir = self._storage.cover_dir(cover_id)
        vocals = work_dir / "converted_vocals.wav"
        instrumental = _find_instrumental(work_dir)
        if not vocals.exists() or instrumental is None:
            raise ConflictError(
                "재믹싱에 필요한 중간 파일이 없어요. 새 커버로 다시 만들어주세요."
            )
        result = get_engine_set().mixer.mix(
            vocals, instrumental, work_dir / "cover.wav", vocal_gain, 1.0
        )
        crud.set_vocal_gain(self._db, cover_id, vocal_gain)
        crud.set_completed(self._db, cover_id, str(result))
        _invalidate_waveform_cache(work_dir)
        return self.get(cover_id)

    def get(self, cover_id: int) -> CoverJob:
        cover = crud.get_cover(self._db, cover_id)
        if cover is None:
            raise NotFoundError(f"Cover {cover_id} not found.")
        return cover

    def delete(self, cover_id: int) -> None:
        cover = self.get(cover_id)
        if cover.status in _IN_PROGRESS_STATUSES:
            raise ConflictError("진행 중인 커버는 삭제할 수 없어요. 완료되면 삭제해주세요.")
        self._storage.remove_cover_data(cover_id, Path(cover.song_path))
        crud.delete_cover(self._db, cover)

    def delete_many(self, cover_ids: Sequence[int]) -> tuple[int, int]:
        """Bulk delete for the library's compact mode. In-progress or already
        deleted covers are skipped instead of failing the whole batch."""
        deleted = 0
        skipped = 0
        for cover_id in cover_ids:
            cover = crud.get_cover(self._db, cover_id)
            if cover is None or cover.status in _IN_PROGRESS_STATUSES:
                skipped += 1
                continue
            self._storage.remove_cover_data(cover.id, Path(cover.song_path))
            crud.delete_cover(self._db, cover)
            deleted += 1
        return deleted, skipped

    def list_all(self, voice_id: int | None = None) -> Sequence[CoverJob]:
        return crud.list_covers(self._db, voice_id)

    def retry(self, cover_id: int) -> CoverJob:
        cover = self.get(cover_id)
        if cover.status is not CoverStatus.FAILED:
            raise ConflictError("실패한 커버만 다시 시도할 수 있어요.")
        voice = voices_crud.get_voice(self._db, cover.voice_id)
        if voice is None or voice.status is not VoiceStatus.READY:
            raise ConflictError("보이스가 사용 가능 상태일 때만 다시 시도할 수 있어요.")
        if not Path(cover.song_path).exists():
            raise ConflictError("원곡 파일이 남아있지 않아요. 새 커버로 다시 만들어주세요.")
        crud.reset_for_retry(self._db, cover_id)
        self._runner.submit(partial(execute_cover, cover_id))
        return self.get(cover_id)

    def get_result(self, cover_id: int) -> tuple[Path, str]:
        """Return the rendered file path and a download filename."""
        cover = self.get(cover_id)
        if cover.status is not CoverStatus.COMPLETED or cover.result_path is None:
            raise ConflictError("This cover has not finished rendering yet.")
        download_name = f"{Path(cover.title).stem}_cover{Path(cover.result_path).suffix}"
        return Path(cover.result_path), download_name

    def get_stem(self, cover_id: int, kind: str) -> Path:
        """The separated stems kept per cover, for the multitrack studio player:
        the AI-converted vocal and the instrumental (MR)."""
        cover = self.get(cover_id)
        if cover.status is not CoverStatus.COMPLETED:
            raise ConflictError("완성된 커버만 트랙을 열 수 있어요.")
        work_dir = self._storage.cover_dir(cover_id)
        if kind == "vocal":
            path: Path | None = work_dir / "converted_vocals.wav"
            if not path.exists():
                path = None
        else:
            path = _find_instrumental(work_dir)
        if path is None or not path.exists():
            raise NotFoundError(
                "트랙 파일이 없어요. 예전에 만든 커버라면 새로 만들어야 트랙이 생겨요."
            )
        return path

    def get_export(self, cover_id: int) -> tuple[Path, str]:
        """MP3 for download/upload. Transcodes the rendered WAV once and caches
        it; falls back to the WAV if ffmpeg is unavailable (e.g. mock engine)."""
        result_path, _ = self.get_result(cover_id)
        stem = Path(self.get(cover_id).title).stem
        mp3_path = result_path.parent / "cover.mp3"
        fresh = mp3_path.exists() and mp3_path.stat().st_mtime >= result_path.stat().st_mtime
        if not fresh:
            try:
                run_command(
                    ["ffmpeg", "-y", "-i", str(result_path),
                     "-c:a", "libmp3lame", "-b:a", "320k", str(mp3_path)]
                )
            except EngineError:
                logger.warning("MP3 transcode failed for cover %s; serving WAV.", cover_id)
                return result_path, f"{stem}_cover.wav"
        return mp3_path, f"{stem}_cover.mp3"

    def get_waveform(self, cover_id: int) -> list[float]:
        """Peaks of the rendered audio, cached alongside the result file."""
        result_path, _ = self.get_result(cover_id)
        cache_path = result_path.parent / "waveform.json"
        if cache_path.exists() and cache_path.stat().st_mtime >= result_path.stat().st_mtime:
            cached: list[float] = json.loads(cache_path.read_text())
            return cached
        try:
            peaks = compute_waveform_peaks(result_path)
        except EngineError as error:
            raise ConflictError(f"파형을 계산할 수 없어요: {error}") from error
        cache_path.write_text(json.dumps(peaks))
        return peaks


def execute_cover(cover_id: int) -> None:
    """Background entrypoint: separate -> convert -> mix, persisting each stage."""
    with SessionLocal() as db:
        cover = crud.get_cover(db, cover_id)
        if cover is None:
            return
        voice = voices_crud.get_voice(db, cover.voice_id)
        if voice is None or voice.model_path is None:
            crud.set_failed(db, cover_id, "Voice model is unavailable.")
            return
        song_path = Path(cover.song_path)
        vocal_gain = cover.vocal_gain
        conversion = _ConversionOptions(
            transpose=cover.transpose,
            index_rate=cover.index_rate,
            protect=cover.protect,
            volume_envelope=cover.volume_envelope,
        )
        model_path = Path(voice.model_path)
        auto_pitch = None
        if cover.auto_transpose:
            auto_pitch = _AutoPitch(
                voice_id=voice.id,
                voice_f0_hz=voice.median_f0_hz,
                dataset_paths=tuple(
                    Path(item.stored_path) for item in voice.dataset_files
                ),
            )
    try:
        result = _render_cover(
            cover_id, song_path, model_path, conversion, vocal_gain, auto_pitch
        )
    except Exception as exc:
        logger.exception("Cover job %s failed.", cover_id)
        with SessionLocal() as db:
            crud.set_failed(db, cover_id, str(exc))
        return
    with SessionLocal() as db:
        crud.set_completed(db, cover_id, str(result))


# Progress budget for a cover job. The SEPARATING slice is shared evenly by
# however many separator-grade prep passes run (vocal split, karaoke split,
# de-reverb) — each costs roughly the same per song-second.
_SEPARATION_RANGE = (0.05, 0.55)
_CONVERSION_RANGE = (0.6, 0.9)


def _prep_slices(count: int) -> list[tuple[float, float]]:
    start, end = _SEPARATION_RANGE
    width = (end - start) / count
    return [(start + index * width, start + (index + 1) * width) for index in range(count)]
_MIXING_AT = 0.92
_STAGE_OVERHEAD_S = 20.0
_TICK_INTERVAL_S = 2.0


@dataclass(frozen=True)
class _StagePlan:
    status: CoverStatus
    progress_range: tuple[float, float]
    estimate_seconds: float | None
    tail_seconds: float
    """Estimated duration of the stages that come after this one."""


class _StageTicker:
    """Writes time-based progress/ETA while a stage that emits no progress
    signal runs (audio-separator and Applio infer are silent on pipes).

    Progress within the stage advances by elapsed/estimate and is capped just
    short of the stage end so the bar never lies about being done.
    """

    def __init__(self, cover_id: int, plan: _StagePlan) -> None:
        self._cover_id = cover_id
        self._plan = plan
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def __enter__(self) -> "_StageTicker":
        initial_eta = (
            None
            if self._plan.estimate_seconds is None
            else self._plan.estimate_seconds + self._plan.tail_seconds
        )
        _set_stage(self._cover_id, self._plan.status, self._plan.progress_range[0], initial_eta)
        self._thread.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._stop.set()
        self._thread.join(timeout=_TICK_INTERVAL_S * 3)

    def _run(self) -> None:
        estimate = self._plan.estimate_seconds
        if estimate is None or estimate <= 0:
            return
        low, high = self._plan.progress_range
        started = time.monotonic()
        while not self._stop.wait(_TICK_INTERVAL_S):
            elapsed = time.monotonic() - started
            fraction = min(elapsed / estimate, 0.98)
            eta = max(estimate - elapsed, 2.0) + self._plan.tail_seconds
            _set_stage(self._cover_id, self._plan.status, low + (high - low) * fraction, eta)


@dataclass(frozen=True)
class _ConversionOptions:
    transpose: int
    index_rate: float
    protect: float
    volume_envelope: float


@dataclass(frozen=True)
class _AutoPitch:
    """Inputs for resolving the auto key shift inside the background job."""

    voice_id: int
    voice_f0_hz: float | None
    dataset_paths: tuple[Path, ...]


def _resolve_auto_transpose(cover_id: int, auto_pitch: _AutoPitch, vocals: Path) -> int:
    """Octave shift matching the song's vocal register to the voice model's.

    The voice register is measured from its dataset once and cached on the
    voice row. Any measurement failure falls back to no shift — a wrong octave
    is worse than none.
    """
    analyzer = get_engine_set().pitch_analyzer
    voice_f0 = auto_pitch.voice_f0_hz
    if voice_f0 is None:
        existing = [path for path in auto_pitch.dataset_paths if path.exists()]
        voice_f0 = analyzer.median_f0(existing) if existing else None
        if voice_f0 is not None:
            with SessionLocal() as db:
                voices_crud.set_median_f0(db, auto_pitch.voice_id, voice_f0)
    if voice_f0 is None:
        logger.warning("Voice %s register unknown; skipping auto key.", auto_pitch.voice_id)
        return 0
    source_f0 = analyzer.median_f0([vocals])
    if source_f0 is None:
        logger.warning("Cover %s vocal register unknown; skipping auto key.", cover_id)
        return 0
    shift = octave_shift_semitones(voice_f0, source_f0)
    logger.info(
        "Cover %s auto key: voice %.1f Hz, song %.1f Hz -> %+d semitones.",
        cover_id, voice_f0, source_f0, shift,
    )
    return shift


def _render_cover(
    cover_id: int,
    song_path: Path,
    model_path: Path,
    conversion: _ConversionOptions,
    vocal_gain: float,
    auto_pitch: _AutoPitch | None = None,
) -> Path:
    engines = get_engine_set()
    work_dir = get_file_storage().cover_dir(cover_id)
    separation_estimate, conversion_estimate = _stage_estimates(song_path)

    total_passes = (
        1 + (engines.karaoke is not None) + (engines.dereverber is not None)
    )
    slices = _prep_slices(total_passes)
    pass_index = 0

    def next_prep_plan() -> _StagePlan:
        nonlocal pass_index
        remaining_after = total_passes - pass_index - 1
        plan = _StagePlan(
            status=CoverStatus.SEPARATING,
            progress_range=slices[pass_index],
            estimate_seconds=separation_estimate,
            tail_seconds=(separation_estimate or 0.0) * remaining_after
            + (conversion_estimate or 0.0)
            + 5.0,
        )
        pass_index += 1
        return plan

    with _StageTicker(cover_id, next_prep_plan()):
        separated = engines.separator.separate(song_path, work_dir, _ignore_progress)

    vocals = separated.vocals
    accompaniment = separated.instrumental

    if engines.karaoke is not None:
        with _StageTicker(cover_id, next_prep_plan()):
            lead, backing = engines.karaoke.split(vocals, work_dir)
        backing_level = mean_volume_db(backing)
        if backing_level is None or backing_level > get_settings().karaoke_backing_floor_db:
            # 코러스가 실제로 있는 곡: 리드만 변환하고 코러스는 반주에 남긴다.
            vocals = lead
            accompaniment = engines.mixer.merge(
                [separated.instrumental, backing], work_dir / "accompaniment.wav"
            )
        # 코러스가 사실상 없으면 원 보컬을 그대로 써서 카라오케 패스의
        # 아티팩트를 피한다.

    if engines.dereverber is not None:
        with _StageTicker(cover_id, next_prep_plan()):
            vocals = engines.dereverber.dereverb(vocals, work_dir)

    if auto_pitch is not None:
        transpose = _resolve_auto_transpose(cover_id, auto_pitch, vocals)
        conversion = replace(conversion, transpose=transpose)
        with SessionLocal() as db:
            crud.set_transpose(db, cover_id, transpose)

    conversion_plan = _StagePlan(
        status=CoverStatus.CONVERTING,
        progress_range=_CONVERSION_RANGE,
        estimate_seconds=conversion_estimate,
        tail_seconds=5.0,
    )
    spec = ConversionSpec(
        source_vocals=vocals,
        model_path=model_path,
        output_path=work_dir / "converted_vocals.wav",
        transpose=conversion.transpose,
        index_rate=conversion.index_rate,
        protect=conversion.protect,
        volume_envelope=conversion.volume_envelope,
    )
    with _StageTicker(cover_id, conversion_plan):
        converted = engines.converter.convert(spec)

    _set_stage(cover_id, CoverStatus.MIXING, _MIXING_AT, None)
    return engines.mixer.mix(
        converted, accompaniment, work_dir / "cover.wav", vocal_gain, 1.0
    )


def _stage_estimates(song_path: Path) -> tuple[float | None, float | None]:
    """Per-stage time estimates from the song duration; (None, None) if unknown."""
    duration = audio_duration_seconds(song_path)
    if duration is None:
        return None, None
    settings = get_settings()
    separation = _STAGE_OVERHEAD_S + duration * settings.separation_speed_factor
    conversion = _STAGE_OVERHEAD_S / 2 + duration * settings.conversion_speed_factor
    return separation, conversion


def _ignore_progress(progress: float) -> None:
    """Separator progress is time-estimated by _StageTicker instead."""


# The non-vocal stem's label varies by separator model: classic models emit
# "(Instrumental)"; 2-stem vocal models (vocals_mel_band_roformer) emit "(other)".
_INSTRUMENTAL_MARKERS = ("instrumental", "no vocals", "(other)")


def _find_instrumental(work_dir: Path) -> Path | None:
    # 코러스가 있는 곡은 반주+코러스 합본이 따로 저장된다 — 리믹싱과 스튜디오
    # 재생 모두 이쪽을 써야 최종 믹스와 밸런스가 같다.
    accompaniment = work_dir / "accompaniment.wav"
    if accompaniment.exists():
        return accompaniment
    for candidate in work_dir.glob("*.wav"):
        name = candidate.name.lower()
        if any(marker in name for marker in _INSTRUMENTAL_MARKERS):
            return candidate
    return None


def _invalidate_waveform_cache(work_dir: Path) -> None:
    (work_dir / "waveform.json").unlink(missing_ok=True)


def _set_stage(
    cover_id: int, status: CoverStatus, progress: float, eta_seconds: float | None
) -> None:
    with SessionLocal() as db:
        crud.set_stage(db, cover_id, status, progress, eta_seconds)


def get_cover_service(db: Session = Depends(get_db)) -> CoverService:
    return CoverService(db=db, storage=get_file_storage(), runner=get_job_runner())
