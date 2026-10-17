"""Round 6: AI labellers A1 (OpenAI) and A2 (Google) on a packet, one row per request.

Each request carries only the human instructions and one row (title, abstract,
arXiv id, date). Outputs go to data/controversies/r6/sealed/<packet>_<labeller>.jsonl.
Usage: python controversies/r6_ai_label.py A
"""
import csv, json, os, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R6 = ROOT / "data/controversies/r6"
LABELLERS = {"A1": ("openai", "gpt-5.5-2026-04-23"), "A2": ("google", "gemini-3.8-flash")}
SCHEMA = {"A": 'Reply with JSON only: {"is_contested_anomalous_claim": "yes" or "no", "key_phrase_used_by_later_papers": string (empty if no), "notes": string}'}


class DailyQuota(Exception):
    pass


STOP = {"quota": False}


def http(url, body, headers):
    for attempt in range(8):
        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"content-type": "application/json", **headers})
            with urllib.request.urlopen(req, timeout=300) as r: return json.loads(r.read())
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            if isinstance(e, urllib.error.HTTPError):
                detail = e.read().decode()
                if e.code == 429 and "PerDay" in detail: raise DailyQuota(detail[:200])  # free tier: resume tomorrow
                if e.code not in (429, 500, 502, 503, 504): raise RuntimeError(detail[:300])
            time.sleep(min(60, 2 ** attempt))
    raise RuntimeError("retries exhausted")


def ask(vendor, model, prompt):
    if vendor == "openai":
        r = http("https://api.openai.com/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": prompt}],
                 "response_format": {"type": "json_object"}}, {"authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"})
        return r["choices"][0]["message"]["content"]
    r = http(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={os.environ['GEMINI_API_KEY']}",
             {"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}}, {})
    return "".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"])


def main(packet):
    instructions = (R6 / f"INSTRUCTIONS_packet_{packet}.md").read_text()
    rows = list(csv.DictReader((R6 / ("packet_A_screening.csv" if packet == "A" else "packet_B_outcomes.csv")).open()))
    fields = ["rank", "arxiv_id", "date", "title", "abstract", "round5_case_flag"] if packet == "A" else [k for k in rows[0] if not k.startswith("label") and k not in ("reason", "reference")]
    out_dir = R6 / "sealed"; out_dir.mkdir(exist_ok=True)
    for name, (vendor, model) in LABELLERS.items():
        path = out_dir / f"packet_{packet}_{name}.jsonl"
        done = {json.loads(l)["row"] for l in path.open() if '"error' not in json.loads(l)["response"]} if path.exists() else set()
        todo = [r for r in rows if (r.get("rank") or r.get("case_id")) not in done]

        def one(r):
            if STOP["quota"]: return None
            row = {k: r[k] for k in fields if k in r}
            prompt = f"{instructions}\n\n---\nYou are one independent labeller. Label this single row.\n\n{json.dumps(row, ensure_ascii=False, indent=1)}\n\n{SCHEMA.get(packet, '')}"
            try: text = ask(vendor, model, prompt)
            except DailyQuota:
                STOP["quota"] = True; return None
            except Exception as e: text = json.dumps({"error": str(e)[:300]})
            return dict(row=r.get("rank") or r.get("case_id"), labeller=name, model=model, response=text)

        with ThreadPoolExecutor(8 if vendor == "openai" else 2) as pool, path.open("a") as f:
            for res in pool.map(one, todo):
                if res is None: continue
                f.write(json.dumps(res, ensure_ascii=False) + "\n"); f.flush()
        good = {json.loads(l)["row"] for l in path.open() if '"error' not in json.loads(l)["response"]}
        print(name, model, "rows", len(rows), "labelled", len(good), "daily quota hit" if STOP["quota"] else "")
        STOP["quota"] = False


if __name__ == "__main__":
    main(sys.argv[1])
