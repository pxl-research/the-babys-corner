"""One-time script: generate compact_description for every stroller in catalog.json.

Usage (from backend/):
    python -m scripts.generate_compact_descriptions

Skips strollers that already have compact_description.
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
        env[key.strip()] = val.strip().strip('"').strip("'")
    return env


# ---------------------------------------------------------------------------
# LLM call via raw urllib (no SDK — avoids arch mismatch)
# ---------------------------------------------------------------------------

SYSTEM = (
    "Je bent een productspecialist kinderwagens. "
    "Maak een compacte beschrijving van maximaal 15 woorden in het Nederlands. "
    "Vermeld: terreintype (stad/terrein/universeel), mobiliteit (lichtgewicht/compact/zwaar), "
    "en maximaal 3 onderscheidende kenmerken. "
    "Geen marketing-taal, geen merk herhalen, alleen feitelijke attributen. "
    "Geef enkel de beschrijving, geen uitleg."
)


async def _compact(
    stroller: dict,
    endpoint: str,
    api_key: str,
    model: str,
    semaphore: asyncio.Semaphore,
) -> str | None:
    prompt = (
        f"Naam: {stroller['name']}\n"
        f"Prijs: €{stroller['price']:.0f}\n"
        f"Beschrijving: {stroller['description'][:600]}"
    )
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "max_completion_tokens": 2048,
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
                    timeout=60,
                )
                return json.loads(result.stdout.decode())

            data = await loop.run_in_executor(None, _do_request)
            if "choices" not in data:
                print(f"  API ERROR {stroller['id']}: {json.dumps(data)[:200]}", file=sys.stderr)
                return None
            content = data["choices"][0]["message"]["content"]
            return content.strip() if content else None
        except Exception as e:
            print(f"  ERROR {stroller['id']} ({stroller['name'][:40]}): {e}", file=sys.stderr)
            return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

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
    todo = [s for s in strollers if not s.get("compact_description")]
    already_done = len(strollers) - len(todo)
    print(f"Strollers: {len(strollers)} total, {already_done} already done, {len(todo)} to generate")
    print(f"Model: {model}  Endpoint: {endpoint[:40]}...")

    if not todo:
        print("Nothing to do.")
        return

    semaphore = asyncio.Semaphore(3)
    batch_size = 10
    completed = 0

    for batch_start in range(0, len(todo), batch_size):
        batch = todo[batch_start : batch_start + batch_size]
        tasks = [_compact(s, endpoint, api_key, model, semaphore) for s in batch]
        results = await asyncio.gather(*tasks)

        for stroller, result in zip(batch, results):
            if result:
                stroller["compact_description"] = result
                completed += 1
                print(f"  [{completed}/{len(todo)}] {stroller['id']}: {result}")
            else:
                print(f"  SKIP {stroller['id']} — no result")

        with open(CATALOG_PATH, "w", encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)
        print(f"  Saved ({batch_start + len(batch)}/{len(todo)} processed)")

    print(f"\nDone. {completed}/{len(todo)} compact descriptions generated.")


if __name__ == "__main__":
    asyncio.run(main())
