from collections.abc import Sequence
from pathlib import Path

from fastapi import Depends, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ConflictError, InvalidInputError, NotFoundError
from app.features.voices import crud
from app.features.voices.models import DatasetFile, Voice, VoiceStatus
from app.features.voices.schemas import VoiceCreate, VoiceUpdate
from app.storage.files import FileStorage, get_file_storage

ALLOWED_AUDIO_SUFFIXES = frozenset({".wav", ".mp3", ".flac", ".m4a", ".ogg"})


class VoiceService:
    def __init__(self, db: Session, storage: FileStorage) -> None:
        self._db = db
        self._storage = storage

    def create(self, data: VoiceCreate) -> Voice:
        if crud.get_voice_by_name(self._db, data.name) is not None:
            raise ConflictError(f"Voice named '{data.name}' already exists.")
        return crud.create_voice(self._db, data.name, data.description)

    def get(self, voice_id: int) -> Voice:
        voice = crud.get_voice(self._db, voice_id)
        if voice is None:
            raise NotFoundError(f"Voice {voice_id} not found.")
        return voice

    def update(self, voice_id: int, data: VoiceUpdate) -> Voice:
        voice = self.get(voice_id)
        duplicate = crud.get_voice_by_name(self._db, data.name)
        if duplicate is not None and duplicate.id != voice_id:
            raise ConflictError(f"'{data.name}' 이름의 보이스가 이미 있어요.")
        return crud.update_voice(self._db, voice, data.name, data.description)

    def list_all(self) -> Sequence[Voice]:
        return crud.list_voices(self._db)

    def delete(self, voice_id: int) -> None:
        voice = self.get(voice_id)
        if voice.status is VoiceStatus.TRAINING:
            raise ConflictError("Cannot delete a voice while it is training.")
        self._storage.remove_voice_data(voice_id)
        crud.delete_voice(self._db, voice)

    def add_dataset_files(
        self, voice_id: int, uploads: Sequence[UploadFile]
    ) -> list[DatasetFile]:
        voice = self.get(voice_id)
        if voice.status is VoiceStatus.TRAINING:
            raise ConflictError("Cannot modify the dataset while the voice is training.")
        if not uploads:
            raise InvalidInputError("At least one audio file is required.")
        stored = [self._store_dataset_file(voice_id, upload) for upload in uploads]
        # 데이터셋이 바뀌면 캐시된 음역(자동 키 매칭용)은 무효 — 다음 자동 키
        # 커버에서 다시 측정한다.
        crud.reset_median_f0(self._db, voice_id)
        return stored

    def _store_dataset_file(self, voice_id: int, upload: UploadFile) -> DatasetFile:
        original_name = validate_audio_filename(upload.filename)
        stored = self._storage.save_upload(upload, self._storage.dataset_dir(voice_id))
        return crud.add_dataset_file(
            self._db, voice_id, original_name, str(stored), upload.size or 0
        )


def validate_audio_filename(filename: str | None) -> str:
    name = filename or ""
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_AUDIO_SUFFIXES:
        allowed = ", ".join(sorted(ALLOWED_AUDIO_SUFFIXES))
        raise InvalidInputError(
            f"Unsupported audio format '{suffix or name}'. Allowed: {allowed}."
        )
    return name


def get_voice_service(db: Session = Depends(get_db)) -> VoiceService:
    return VoiceService(db=db, storage=get_file_storage())
