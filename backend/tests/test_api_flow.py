import time
from collections.abc import Callable

from fastapi.testclient import TestClient

from app.main import app

TERMINAL_STATUSES = {"completed", "failed"}


def _poll_until_terminal(fetch: Callable[[], dict[str, object]], timeout: float = 15.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        payload = fetch()
        if payload["status"] in TERMINAL_STATUSES:
            return payload
        time.sleep(0.1)
    raise AssertionError("Job did not reach a terminal status in time.")


def test_full_cover_flow() -> None:
    with TestClient(app) as client:
        assert client.get("/api/v1/health").json() == {"status": "ok"}

        # 1. Create a voice.
        created = client.post(
            "/api/v1/voices", json={"name": "Test Singer", "description": "smoke test"}
        )
        assert created.status_code == 201
        voice_id = created.json()["id"]

        # 2. Upload dataset audio.
        uploaded = client.post(
            f"/api/v1/voices/{voice_id}/dataset",
            files=[("files", ("sample.wav", b"RIFF-fake-wav-bytes", "audio/wav"))],
        )
        assert uploaded.status_code == 201

        # 3. Train and wait for the mock trainer to finish.
        started = client.post("/api/v1/trainings", json={"voice_id": voice_id, "epochs": 10})
        assert started.status_code == 202
        job_id = started.json()["id"]
        job = _poll_until_terminal(
            lambda: dict(client.get(f"/api/v1/trainings/{job_id}").json())
        )
        assert job["status"] == "completed"
        assert client.get(f"/api/v1/voices/{voice_id}").json()["status"] == "ready"

        # 4. Generate a cover and download the result.
        cover_created = client.post(
            "/api/v1/covers",
            data={"voice_id": str(voice_id), "transpose": "0"},
            files={"song": ("song.mp3", b"ID3-fake-mp3-bytes", "audio/mpeg")},
        )
        assert cover_created.status_code == 202
        cover_id = cover_created.json()["id"]
        cover = _poll_until_terminal(
            lambda: dict(client.get(f"/api/v1/covers/{cover_id}").json())
        )
        assert cover["status"] == "completed"

        audio = client.get(f"/api/v1/covers/{cover_id}/audio")
        assert audio.status_code == 200
        assert audio.content

        # 5. Re-mix at a louder vocal volume without re-running the pipeline.
        remixed = client.post(
            f"/api/v1/covers/{cover_id}/remix", json={"vocal_gain": 2.0}
        )
        assert remixed.status_code == 200
        assert remixed.json()["vocal_gain"] == 2.0
        assert remixed.json()["status"] == "completed"

        # 6. Delete the cover.
        assert client.delete(f"/api/v1/covers/{cover_id}").status_code == 204
        assert client.get(f"/api/v1/covers/{cover_id}").status_code == 404


def test_rejects_cover_for_untrained_voice() -> None:
    with TestClient(app) as client:
        voice_id = client.post(
            "/api/v1/voices", json={"name": "Untrained", "description": ""}
        ).json()["id"]
        response = client.post(
            "/api/v1/covers",
            data={"voice_id": str(voice_id)},
            files={"song": ("song.mp3", b"bytes", "audio/mpeg")},
        )
        assert response.status_code == 409


def test_cancel_rejects_finished_training() -> None:
    with TestClient(app) as client:
        voice_id = client.post(
            "/api/v1/voices", json={"name": "Cancel Target", "description": ""}
        ).json()["id"]
        client.post(
            f"/api/v1/voices/{voice_id}/dataset",
            files=[("files", ("s.wav", b"bytes", "audio/wav"))],
        )
        job_id = client.post(
            "/api/v1/trainings", json={"voice_id": voice_id, "epochs": 5}
        ).json()["id"]
        _poll_until_terminal(
            lambda: dict(client.get(f"/api/v1/trainings/{job_id}").json())
        )
        # A finished job can no longer be cancelled.
        assert client.post(f"/api/v1/trainings/{job_id}/cancel").status_code == 409


def test_rejects_non_audio_dataset_upload() -> None:
    with TestClient(app) as client:
        voice_id = client.post(
            "/api/v1/voices", json={"name": "Bad Upload", "description": ""}
        ).json()["id"]
        response = client.post(
            f"/api/v1/voices/{voice_id}/dataset",
            files=[("files", ("notes.txt", b"hello", "text/plain"))],
        )
        assert response.status_code == 422
