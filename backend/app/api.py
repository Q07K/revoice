from fastapi import APIRouter

from app.features.covers.router import router as covers_router
from app.features.separations.router import router as separations_router
from app.features.trainings.router import router as trainings_router
from app.features.videos.router import router as videos_router
from app.features.voices.router import router as voices_router

api_router = APIRouter()
api_router.include_router(voices_router)
api_router.include_router(trainings_router)
api_router.include_router(covers_router)
api_router.include_router(separations_router)
api_router.include_router(videos_router)


@api_router.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
