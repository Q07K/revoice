from fastapi import APIRouter

from app.features.covers.router import router as covers_router
from app.features.trainings.router import router as trainings_router
from app.features.voices.router import router as voices_router

api_router = APIRouter()
api_router.include_router(voices_router)
api_router.include_router(trainings_router)
api_router.include_router(covers_router)


@api_router.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
