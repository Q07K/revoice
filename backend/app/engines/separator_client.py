"""Client for the persistent audio-separator worker (scripts/separator_daemon.py).

Each CLI invocation of audio-separator pays 20~30s of model loading before any
work happens, and a cover runs up to three separator-grade passes (vocal split,
karaoke split, de-reverb). The daemon keeps the loaded models resident in the
separator venv's process, so repeat passes start instantly. Any daemon failure
is surfaced as EngineError; callers fall back to the CLI.
"""

import json
import logging
import subprocess
import threading
from functools import lru_cache
from pathlib import Path

from app.engines.base import EngineError, subprocess_env

logger = logging.getLogger(__name__)

_SCRIPT = Path(__file__).parent / "scripts" / "separator_daemon.py"
# 첫 기동은 CUDA 초기화 + 임포트 시간이 든다.
_READY_TIMEOUT_S = 180.0


class SeparatorDaemon:
    """Serialized (one request at a time) — GPU passes don't parallelize
    usefully anyway, and the protocol is a simple request/response pipe."""

    def __init__(self, python_bin: str) -> None:
        self._python_bin = python_bin
        self._lock = threading.Lock()
        self._process: subprocess.Popen[str] | None = None

    def separate(self, model: str, input_path: Path, output_dir: Path) -> None:
        with self._lock:
            process = self._ensure_process()
            request = json.dumps(
                {"model": model, "input": str(input_path), "output_dir": str(output_dir)}
            )
            try:
                assert process.stdin is not None and process.stdout is not None
                process.stdin.write(request + "\n")
                process.stdin.flush()
                line = process.stdout.readline()
            except (OSError, ValueError) as error:
                self._kill()
                raise EngineError(f"Separator daemon I/O failed: {error}") from error
            if not line:
                self._kill()
                raise EngineError("Separator daemon exited unexpectedly.")
            try:
                response = json.loads(line)
            except json.JSONDecodeError as error:
                self._kill()
                raise EngineError(f"Separator daemon spoke garbage: {line[:200]}") from error
            if not response.get("ok"):
                raise EngineError(f"Separator daemon error: {response.get('error')}")

    def _ensure_process(self) -> "subprocess.Popen[str]":
        if self._process is not None and self._process.poll() is None:
            return self._process
        logger.info("Starting separator daemon: %s", self._python_bin)
        process = subprocess.Popen(
            [self._python_bin, str(_SCRIPT)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            # stderr를 파이프로 두면 가득 찼을 때 교착된다 — 진단은 JSON 응답의
            # error 필드로 충분하다.
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            env=subprocess_env(),
        )
        ready: list[str] = []

        def wait_ready() -> None:
            if process.stdout is not None:
                ready.append(process.stdout.readline())

        waiter = threading.Thread(target=wait_ready, daemon=True)
        waiter.start()
        waiter.join(_READY_TIMEOUT_S)
        if not ready or not ready[0].strip():
            process.kill()
            raise EngineError("Separator daemon failed to become ready.")
        self._process = process
        return process

    def _kill(self) -> None:
        if self._process is not None:
            self._process.kill()
            self._process = None


@lru_cache
def get_separator_daemon(python_bin: str) -> SeparatorDaemon:
    return SeparatorDaemon(python_bin)
