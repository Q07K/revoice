"""Long-lived audio-separator worker: keeps models loaded across requests.

Runs inside the separator venv. Speaks newline-delimited JSON over
stdin/stdout: {"model": ..., "input": ..., "output_dir": ...} in,
{"ok": true, "files": [...]} or {"ok": false, "error": ...} out. Loading a
RoFormer checkpoint takes 20~30s, so caching one Separator per model removes
that overhead from every separation pass (covers run up to three passes).
"""

import json
import sys
import traceback


def main() -> None:
    from audio_separator.separator import Separator

    separators: dict[str, Separator] = {}

    # Signal readiness so the client can wait for import/CUDA warmup.
    print(json.dumps({"ready": True}), flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            model = request["model"]
            separator = separators.get(model)
            if separator is None:
                separator = Separator(
                    log_level=40,  # ERROR — stdout must stay JSON-only
                    output_dir=request["output_dir"],
                    output_format="wav",
                )
                separator.load_model(model_filename=model)
                separators[model] = separator
            # The loaded model copies output_dir at load time, so update both
            # the facade and the live model instance for reused models.
            separator.output_dir = request["output_dir"]
            if getattr(separator, "model_instance", None) is not None:
                separator.model_instance.output_dir = request["output_dir"]
            files = separator.separate(request["input"])
            print(json.dumps({"ok": True, "files": files}), flush=True)
        except Exception as error:  # noqa: BLE001 — reported to the client
            traceback.print_exc(file=sys.stderr)
            print(json.dumps({"ok": False, "error": str(error)}), flush=True)


if __name__ == "__main__":
    main()
