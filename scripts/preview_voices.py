"""Generate at most three explicitly requested Thai samples; never a full episode."""
import base64
import io
import json
import os
from pathlib import Path
import sys
import wave
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MODEL = "gemini-3.8-flash-tts"


def make_payload(sample):
    return {
        "contents": [{"role": "user", "parts": [{
            "text": sample["text"],
            "speech_metadata": {"style": sample["style"]},
        }]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"voice": sample["voice"]}},
        },
    }


def decode_audio(payload):
    candidates = payload.get("candidates", [])
    if len(candidates) != 1 or candidates[0].get("finishReason") != "STOP":
        raise ValueError("Incomplete or blocked sample")
    parts = candidates[0].get("content", {}).get("parts", [])
    audio_parts = [p["inlineData"] for p in parts if "inlineData" in p]
    if len(audio_parts) != 1:
        raise ValueError("Expected one unary audio file")
    audio = audio_parts[0]
    if audio.get("mimeType", "").split(";")[0].lower() not in {"audio/wav", "audio/x-wav", "audio/wave"}:
        raise ValueError("Unexpected audio type; do not guess PCM parameters")
    data = base64.b64decode(audio["data"], validate=True)
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("Not a WAV container")
    with wave.open(io.BytesIO(data), "rb") as audio_file:
        if audio_file.getnframes() < 1:
            raise ValueError("Empty WAV")
        duration = audio_file.getnframes() / audio_file.getframerate()
    return data, duration


def main():
    if os.environ.get("CONFIRM_GENERATION", "").lower() != "true":
        print("Not started: enable confirm_generation to authorize sample API usage.")
        return 1
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        print("Missing Actions repository secret GEMINI_API_KEY.")
        return 1
    try:
        config = json.loads(Path("config/voice_samples.json").read_text(encoding="utf-8"))
        if config["model"] != MODEL:
            raise ValueError("Unexpected model")
        samples = config["samples"]
        allowed = {"nox", "manager", "lin"}
        if len(samples) != 3 or {s["id"] for s in samples} != allowed:
            raise ValueError("Unexpected samples")
        if any(not s["text"].strip() or len(s["text"]) > 450 for s in samples):
            raise ValueError("Invalid sample length")
        selection = os.environ.get("SAMPLE_CHARACTER", "all")
        if selection not in allowed | {"all"}:
            raise ValueError("Unknown character")
        out = Path("voice-previews")
        out.mkdir(exist_ok=True)
        results = []
        for sample in samples:
            if selection != "all" and sample["id"] != selection:
                continue
            request = Request(
                f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
                data=json.dumps(make_payload(sample), ensure_ascii=False).encode("utf-8"),
                headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                method="POST",
            )
            # Never automatically retry generation: a timeout may still incur usage.
            with urlopen(request, timeout=120) as response:
                payload = json.load(response)
            data, duration = decode_audio(payload)
            name = sample["id"] + ".wav"
            (out / name).write_bytes(data)
            results.append({"file": name, "character": sample["character"],
                            "voice": sample["voice"], "text": sample["text"],
                            "duration_seconds": round(duration, 3),
                            "status": "generated_not_listening_reviewed"})
            (out / "manifest.json").write_text(
                json.dumps({"model": MODEL, "samples": results}, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Saved {name}: {duration:.2f} seconds. Listening review still required.")
        summary = "## Nox Tales voice previews\n\nModel: `" + MODEL + "`\n\n"
        summary += "\n".join(f"- {r['character']}: `{r['file']}` — {r['duration_seconds']} seconds" for r in results)
        summary += "\n\nDownload `nox-voice-previews` below. Voices are provisional; age and Thai delivery need listening review.\n"
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
                f.write(summary)
        return 0
    except HTTPError as error:
        print(f"Gemini returned HTTP {error.code}. No automatic retry; check quota and model permissions.")
    except (URLError, TimeoutError, OSError):
        print("Request or file operation failed. Check saved previews before retrying; API usage may have occurred.")
    except Exception:
        print("Invalid configuration or incomplete audio response. Sensitive diagnostics suppressed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
