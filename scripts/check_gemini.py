"""List accessible Gemini models without generating content or logging secrets."""
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def list_models(api_key, opener=urlopen):
    models = []
    page_token = None
    seen_tokens = set()
    for _ in range(20):
        query = {"pageSize": 100}
        if page_token:
            query["pageToken"] = page_token
        request = Request(
            BASE_URL + "?" + urlencode(query),
            headers={"x-goog-api-key": api_key, "Accept": "application/json"},
        )
        with opener(request, timeout=30) as response:
            payload = json.load(response)
        if not isinstance(payload, dict) or not isinstance(payload.get("models", []), list):
            raise ValueError("Unexpected model-list response")
        for model in payload.get("models", []):
            if not isinstance(model, dict):
                raise ValueError("Unexpected model entry")
            name = model.get("name")
            methods = model.get("supportedGenerationMethods", [])
            if not isinstance(name, str) or not isinstance(methods, list):
                raise ValueError("Unexpected model metadata")
            # Keep only non-secret catalogue fields; do not save raw responses.
            models.append({"name": name, "supportedGenerationMethods": methods})
        page_token = payload.get("nextPageToken")
        if not page_token:
            return models
        if not isinstance(page_token, str) or page_token in seen_tokens:
            raise ValueError("Invalid pagination")
        seen_tokens.add(page_token)
    raise ValueError("Pagination limit reached")


def main():
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("ERROR: Add the repository Actions secret GEMINI_API_KEY.")
        return 1
    try:
        models = list_models(api_key)
    except HTTPError as error:
        # Do not print response bodies, URLs, request headers, or exception text.
        print(f"ERROR: Gemini model listing returned HTTP {error.code}.")
        print("Check API key restrictions, project API access, and request quota.")
        return 1
    except URLError:
        print("ERROR: Cannot reach Gemini API. Check networking and retry later.")
        return 1
    except (ValueError, TimeoutError, OSError):
        print("ERROR: Model-list response was unavailable or invalid.")
        return 1
    except Exception:
        print("ERROR: Connection check failed; sensitive diagnostics suppressed.")
        return 1
    names = sorted({m["name"] for m in models})
    candidates = [n for n in names if "tts" in n.lower()]
    report = {
        "connection": "ok",
        "model_count": len(names),
        "models": models,
        "tts_name_candidates": candidates,
        "generation_performed": False,
        "note": "Name matching is not verification of Thai, voice ages, or TTS availability. Test selected model separately.",
    }
    out = Path("reports")
    out.mkdir(exist_ok=True)
    (out / "gemini-models.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary = [
        "## Gemini connection check",
        "Model listing succeeded. No speech or other content was generated.",
        f"Models listed: {len(names)}",
        "### TTS candidates (name match only)",
    ]
    summary += [f"- `{n}`" for n in candidates] or [
        "No model name containing tts was listed. Inspect the catalogue and official TTS documentation."
    ]
    summary.append("Full catalogue: gemini-model-catalogue artifact. No API key is included.")
    text = "\n\n".join(summary) + "\n"
    (out / "summary.md").write_text(text, encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(text)
    print(f"OK: Gemini API listed {len(names)} models. No generation requested.")
    print(f"TTS name candidates: {len(candidates)}. See the workflow summary.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
