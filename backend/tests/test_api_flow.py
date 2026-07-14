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
            data={
                "voice_id": str(voice_id),
                "transpose": "0",
                "auto_transpose": "true",
                "index_rate": "0.7",
                "protect": "0.25",
                "volume_envelope": "0.8",
            },
            files={"song": ("song.mp3", b"ID3-fake-mp3-bytes", "audio/mpeg")},
        )
        assert cover_created.status_code == 202
        created_body = cover_created.json()
        assert created_body["index_rate"] == 0.7
        assert created_body["protect"] == 0.25
        assert created_body["volume_envelope"] == 0.8
        assert created_body["auto_transpose"] is True
        cover_id = created_body["id"]
        cover = _poll_until_terminal(
            lambda: dict(client.get(f"/api/v1/covers/{cover_id}").json())
        )
        assert cover["status"] == "completed"
        # The mock pitch analyzer can't measure a register, so auto key must
        # fall back to no shift instead of failing the job.
        assert cover["transpose"] == 0

        audio = client.get(f"/api/v1/covers/{cover_id}/audio")
        assert audio.status_code == 200
        assert audio.content

        # Studio: the separated stems are served for multitrack playback.
        for kind in ("vocal", "instrumental"):
            stem = client.get(f"/api/v1/covers/{cover_id}/stems/{kind}/audio")
            assert stem.status_code == 200 and stem.content
        # MP3 export (falls back to WAV under the mock engine's fake audio).
        assert client.get(f"/api/v1/covers/{cover_id}/export.mp3").status_code == 200

        # 5. Re-mix at a louder vocal volume without re-running the pipeline.
        remixed = client.post(
            f"/api/v1/covers/{cover_id}/remix", json={"vocal_gain": 2.0}
        )
        assert remixed.status_code == 200
        assert remixed.json()["vocal_gain"] == 2.0
        assert remixed.json()["status"] == "completed"

        # 5b. Render a YouTube video from the finished cover.
        video_created = client.post(
            "/api/v1/videos",
            data={
                "cover_id": str(cover_id),
                "title": "밤편지",
                "subtitle": "AI 커버",
                "visual": "wave",
                "aspect": "16:9",
            },
            files={"image": ("art.png", b"fake-png", "image/png")},
        )
        assert video_created.status_code == 202
        video_id = video_created.json()["id"]
        video = _poll_until_terminal(
            lambda: dict(client.get(f"/api/v1/videos/{video_id}").json())
        )
        assert video["status"] == "completed"
        assert video["aspect"] == "16:9" and video["visual"] == "wave"
        download = client.get(f"/api/v1/videos/{video_id}/download")
        assert download.status_code == 200 and download.content
        assert client.delete(f"/api/v1/videos/{video_id}").status_code == 204

        # 6. Bulk delete (library compact mode): unknown ids are skipped.
        result = client.post(
            "/api/v1/covers/batch-delete", json={"ids": [cover_id, 999_999]}
        )
        assert result.status_code == 200
        assert result.json() == {"deleted": 1, "skipped": 1}
        assert client.get(f"/api/v1/covers/{cover_id}").status_code == 404


def test_separation_flow() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/separations",
            files={"song": ("song.mp3", b"ID3-fake-mp3-bytes", "audio/mpeg")},
        )
        assert created.status_code == 202
        job_id = created.json()["id"]
        job = _poll_until_terminal(
            lambda: dict(client.get(f"/api/v1/separations/{job_id}").json())
        )
        assert job["status"] == "completed"
        assert job["has_vocals"] and job["has_instrumental"]

        vocals = client.get(f"/api/v1/separations/{job_id}/audio?stem=vocals")
        assert vocals.status_code == 200 and vocals.content
        instrumental = client.get(f"/api/v1/separations/{job_id}/audio?stem=instrumental")
        assert instrumental.status_code == 200 and instrumental.content

        assert client.delete(f"/api/v1/separations/{job_id}").status_code == 204
        assert client.get(f"/api/v1/separations/{job_id}").status_code == 404


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
