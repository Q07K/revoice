from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.features.voices.models import VoiceStatus


class VoiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)


class VoiceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)


class DatasetFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_name: str
    size_bytes: int
    created_at: datetime


class VoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    status: VoiceStatus
    created_at: datetime


class VoiceDetail(VoiceRead):
    dataset_files: list[DatasetFileRead]
