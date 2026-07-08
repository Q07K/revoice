from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.voices.models import DatasetFile, Voice, VoiceStatus


def create_voice(db: Session, name: str, description: str) -> Voice:
    voice = Voice(name=name, description=description)
    db.add(voice)
    db.commit()
    db.refresh(voice)
    return voice


def get_voice(db: Session, voice_id: int) -> Voice | None:
    return db.get(Voice, voice_id)


def get_voice_by_name(db: Session, name: str) -> Voice | None:
    return db.scalar(select(Voice).where(Voice.name == name))


def list_voices(db: Session) -> Sequence[Voice]:
    return db.scalars(select(Voice).order_by(Voice.created_at.desc(), Voice.id.desc())).all()


def delete_voice(db: Session, voice: Voice) -> None:
    db.delete(voice)
    db.commit()


def add_dataset_file(
    db: Session, voice_id: int, original_name: str, stored_path: str, size_bytes: int
) -> DatasetFile:
    dataset_file = DatasetFile(
        voice_id=voice_id,
        original_name=original_name,
        stored_path=stored_path,
        size_bytes=size_bytes,
    )
    db.add(dataset_file)
    db.commit()
    db.refresh(dataset_file)
    return dataset_file


def set_voice_status(
    db: Session, voice_id: int, status: VoiceStatus, model_path: str | None = None
) -> None:
    voice = db.get(Voice, voice_id)
    if voice is None:
        return
    voice.status = status
    if model_path is not None:
        voice.model_path = model_path
    db.commit()
