"""One-time script: generate formatted_description for every stroller in catalog.json.

Reformats the raw description into readable paragraphs + bullet list,
fixing concatenated sentences, missing spaces, and HTML entities.

Usage (from backend/):
    python -m scripts.generate_formatted_descriptions

Skips strollers that already have formatted_description.
Saves catalog.json after every batch so progress is not lost on interruption.
"""
import asyncio
import json
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "catalog" / "catalog.json"
ENV_PATH = ROOT.parent / ".env"


def _load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        val = val.split("#")[0]  # strip inline comments
        env[key.strip()] = val.strip().strip('"').strip("'")
    return env


SYSTEM = (
    "Je bent een redacteur voor een kinderwagenzaak. "
    "Formatteer de ruwe productbeschrijving naar leesbare tekst in het Nederlands. "
    "Regels:\n"
    "- Verdeel lopende tekst in alinea's van 2-4 zinnen (gebruik één lege regel tussen alinea's).\n"
    "- Zet lijstitems (inhoud van het pakket, specificaties, kenmerken) als bulletpunten met '• ' vooraan.\n"
    "- Vervang HTML-entiteiten zoals &amp; door & en &nbsp; door spatie.\n"
    "- Zet sectietitels (bv. 'Standaard in het pakket:') op een eigen regel gevolgd door de bulletpunten.\n"
    "- Voeg geen nieuwe informatie toe en verwijder niets.\n"
    "- Geef enkel de geformatteerde beschrijving, geen uitleg."
)


async def _format(
    stroller: dict,
    endpoint: str,
    api_key: str,
    model: str,
    semaphore: asyncio.Semaphore,
) -> str | None:
    prompt = (
        f"Naam: {stroller['name']}\n"
        f"Ruwe beschrijving:\n{stroller['description']}"
    )
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "max_completion_tokens": 16384,
    }).encode()

    url = f"{endpoint.rstrip('/')}/openai/deployments/{model}/chat/completions?api-version=2024-02-01"

    async with semaphore:
        loop = asyncio.get_running_loop()
        try:
            def _do_request():
                result = subprocess.run(
                    [
                        "curl", "-s", "-X", "POST", url,
                        "-H", "Content-Type: application/json",
                        "-H", f"api-key: {api_key}",
                        "-d", payload.decode(),
                    ],
                    capture_output=True,
                    timeout=120,
                )
                return json.loads(result.stdout.decode())

            data = await asyncio.wait_for(loop.run_in_executor(None, _do_request), timeout=150)
            if "choices" not in data:
                print(f"  API ERROR {stroller['id']}: {json.dumps(data)[:200]}", flush=True)
                return None
            content = data["choices"][0]["message"]["content"]
            if not content:
                finish = data["choices"][0].get("finish_reason")
                usage = data.get("usage", {})
                det = usage.get("completion_tokens_details", {})
                print(f"  EMPTY {stroller['id']}: finish={finish} reasoning={det.get('reasoning_tokens')} total={usage.get('completion_tokens')}", flush=True)
            return content.strip() if content else None
        except Exception as e:
            print(f"  ERROR {stroller['id']} ({stroller['name'][:40]}): {e}", flush=True)
            return None


async def main() -> None:
    env = _load_env(ENV_PATH)
    endpoint = env.get("AZURE_OPENAI_ENDPOINT", "")
    api_key = env.get("AZURE_OPENAI_API_KEY", "")
    model = env.get("AZURE_OPENAI_DEPLOYMENT_MINI", "gpt-5-mini")

    if not endpoint or not api_key:
        print("ERROR: AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY required in .env", file=sys.stderr)
        sys.exit(1)

    with open(CATALOG_PATH, encoding="utf-8") as f:
        catalog = json.load(f)

    strollers = catalog["strollers"]
    todo = [s for s in strollers if not s.get("formatted_description")]
    already_done = len(strollers) - len(todo)
    print(f"Strollers: {len(strollers)} total, {already_done} already done, {len(todo)} to format", flush=True)
    print(f"Model: {model}  Endpoint: {endpoint[:40]}...", flush=True)

    if not todo:
        print("Nothing to do.")
        return

    semaphore = asyncio.Semaphore(1)
    batch_size = 10
    completed = 0

    for batch_start in range(0, len(todo), batch_size):
        batch = todo[batch_start : batch_start + batch_size]
        tasks = [_format(s, endpoint, api_key, model, semaphore) for s in batch]
        results = await asyncio.gather(*tasks)

        for stroller, result in zip(batch, results):
            if result:
                stroller["formatted_description"] = result
                completed += 1
                print(f"  [{completed}/{len(todo)}] {stroller['id']}: OK", flush=True)
            else:
                print(f"  SKIP {stroller['id']} — no result", flush=True)

        with open(CATALOG_PATH, "w", encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)
        print(f"  Saved ({batch_start + len(batch)}/{len(todo)} processed)", flush=True)

    print(f"\nDone. {completed}/{len(todo)} formatted descriptions generated.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
