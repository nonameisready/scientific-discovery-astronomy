"""Build the OpenFindings research object for this paper.

Writes ``paper/openfindings_submission.json``: the full paper as Markdown
(pandoc from ``main.tex``), the complete sealed 2026-2031 forecast table
(``results/prospective2026/forecast.csv``) embedded so agents reading the
record get every prediction, and dataset/code links to the frozen files.

Usage:
    python paper/openfindings_submission.py
"""

import csv
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = "https://github.com/nonameisready/scientific-discovery-astronomy"
BLOB = f"{REPO}/blob/main"
RAW = "https://raw.githubusercontent.com/nonameisready/scientific-discovery-astronomy/main"


# Display-only cleanup for Markdown readers (the frozen question files are
# untouched). Generated questions carry LaTeX whose "\b"/"\t" were decoded as
# control characters upstream ("\beta" -> BACKSPACE+"eta"); restore them, then
# turn simple inline math into Unicode so pages read without a TeX renderer.
_SYMBOLS = {
    r"\times": "×", r"\kappa": "κ", r"\Delta": "Δ", r"\sigma": "σ", r"\beta": "β", r"\alpha": "α",
    r"\Lambda": "Λ", r"\lambda": "λ", r"\mu": "μ", r"\sim": "~", r"\approx": "≈", r"\odot": "⊙",
    r"\textgreater": ">", r"\textless": "<", r"\geq": "≥", r"\leq": "≤", r"\pm": "±", r"\,": " ",
}
_SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def plain_math(text: str) -> str:
    text = text.replace("\x08", "\\b").replace("\t", "\\t").replace("\x0c", "\\f")
    # Some "\t" were decoded as a tab and then normalised to a space upstream
    # ("$ m ext{ extbf{EDE}}$", "z extgreater 10"): restore the backslash, then
    # unwrap text commands and map text symbols inside or outside math.
    text = re.sub(r"(?<=[\s${(])ext(?=\{)|(?<=[\s${(])ext(?=(?:it|bf)\{|greater|less|odot)", r"\\text", text)
    for _ in range(3):
        text = re.sub(r"\\text(?:it|bf)?\{([^{}$]*)\}", r"\1", text)
    text = text.replace(r"\textgreater", ">").replace(r"\textless", "<").replace(r"\textodot", "⊙")
    text = re.sub(r"M_\{?⊙\}?", "M⊙", text)

    def convert(m: re.Match) -> str:
        expr = m.group(1)
        for _ in range(4):  # unwrap nested \text{...}, \textbf{...}, \mathrm{...}
            expr = re.sub(r"\\(?:text|textit|textbf|mathrm|mathbf|rm)\s*\{([^{}]*)\}", r"\1", expr)
        expr = re.sub(r"\\m\s+|^\s*m\s+", "", expr)  # stray "\m" left by a mangled "\mathrm"
        for k in sorted(_SYMBOLS, key=len, reverse=True):
            expr = expr.replace(k, _SYMBOLS[k])
        expr = re.sub(r"_\{?([0-9]+)\}?", lambda d: d.group(1).translate(_SUB), expr)
        expr = re.sub(r"_\{([^{}]*)\}", r"\1", expr)
        expr = expr.replace("{", "").replace("}", "")
        return expr.replace("\\", "").replace("_⊙", "⊙")

    return re.sub(r"\$([^$\n]{1,200})\$", convert, text)


def paper_markdown() -> str:
    md = subprocess.run(
        ["pandoc", "main.tex", "--from=latex", "--to=gfm-raw_html", "--citeproc", "--bibliography=references.bib",
         "--wrap=none"],
        cwd=ROOT / "paper", capture_output=True, text=True, check=True,
    ).stdout
    # Figures: point at the committed PNGs so the record renders anywhere.
    md = md.replace("figures/forest_v3.pdf", f"{RAW}/paper/figures/forest_v3.png")
    md = md.replace("figures/auc_by_cutoff.png", f"{RAW}/paper/figures/auc_by_cutoff.png")
    # Drop the title/author block pandoc emits; the record carries them as fields.
    md = re.sub(r"^.*?(?=# Introduction|<span id=\"introduction\")", "", md, count=1, flags=re.S)
    return plain_math(md.strip())


def forecast_table() -> str:
    rows = list(csv.DictReader((ROOT / "results" / "prospective2026" / "forecast.csv").open()))
    out = [
        "## Appendix: the sealed 2026–2031 forecast (all 200 questions)",
        "",
        "Questions posed on 2026-10-14 from the preceding eight years of arXiv astro-ph. Each probability is that "
        "the question will be **substantively engaged** by astro-ph papers published 2026-10-15 to 2031-10-14 "
        "(Paper 3's label: top-8 TF-IDF-retrieved papers of the subfield, strict gpt-4o judge). It is a forecast "
        "of *uptake*, not of answers or resolution. Ranked by v3; v2 and v1 are shown for the 2031 comparison. "
        f"Frozen with SHA-256 digests: [`FREEZE.json`]({BLOB}/data/prospective2026/FREEZE.json) (v1), "
        f"[`FREEZE_v2.json`]({BLOB}/data/prospective2026/FREEZE_v2.json), "
        f"[`FREEZE_v3.json`]({BLOB}/data/prospective2026/FREEZE_v3.json). "
        f"Machine-readable copy: [`forecast.csv`]({BLOB}/results/prospective2026/forecast.csv) "
        f"([raw]({RAW}/results/prospective2026/forecast.csv)).",
        "",
        "| # | p (v3) | p (v2) | p (v1) | subfield | source | question |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        q = plain_math(r["question"]).replace("|", "\\|").replace("\n", " ")
        out.append(f"| {r['rank']} | {float(r['p_v3']):.2f} | {float(r['p_v2']):.2f} | {float(r['p_attention']):.2f} "
                   f"| {r['subfield']} | {r['source']} | {q} |")
    return "\n".join(out)


def section(md: str, title: str) -> str:
    m = re.search(rf"^#+ {re.escape(title)}.*?$(.*?)(?=^# )", md, flags=re.S | re.M)
    return m.group(1).strip() if m else ""


def main() -> None:
    tex = (ROOT / "paper" / "main.tex").read_text()
    abstract = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", tex, re.S).group(1)
    abstract = subprocess.run(["pandoc", "--from=latex", "--to=plain", "--wrap=none"], input=abstract,
                              capture_output=True, text=True, check=True).stdout.strip()
    body = paper_markdown()
    record = {
        "title": "Topic Momentum Forecasts Which Astronomy Questions the Field Takes Up: Five Pre-registered "
                 "Out-of-Time Backtests and a Sealed 2026–2031 Forecast",
        "abstract": abstract,
        "subject": "Astrophysics",
        "authors": [{"name": "Hui Mao", "affiliation": "Aurora AI Ventures"},
                    {"name": "Claude Code", "affiliation": "Anthropic"}],
        "provenance": {
            "origin": "supervised",
            "operator": "Hui Mao",
            "model": "Claude (Anthropic), working through Claude Code",
        },
        "keywords": ["science of science", "research forecasting", "historical backtesting", "pre-registration",
                     "astronomy", "arXiv astro-ph", "LLM-as-judge", "topic momentum", "sealed forecast"],
        "license": "CC-BY-4.0",
        "methods": section(body, "Setup") + "\n\n" + section(body, "Models"),
        "results": section(body, "Results") + "\n\n" + section(body, "Validity checks"),
        "conclusions": section(body, "Conclusion") + "\n\n" + section(body, "Limitations and deviations"),
        "body_markdown": body + "\n\n" + forecast_table(),
        "datasets": [
            {"name": "Sealed 2026–2031 forecast (200 questions, v1/v2/v3 probabilities)",
             "url": f"{BLOB}/results/prospective2026/forecast.csv", "format": "text/csv"},
            {"name": "Freeze manifests with SHA-256 digests (v1, v2, v3)",
             "url": f"{REPO}/tree/main/data/prospective2026"},
            {"name": "Five backtest cohorts: questions, features, frozen predictions, labels",
             "url": f"{REPO}/tree/main/data"},
            {"name": "Pre-registrations (rounds 1–4)", "url": f"{REPO}/tree/main/docs"},
        ],
        "code": [{"name": "scientific-discovery-astronomy", "url": REPO, "license": "see repository"}],
        "references": [
            {"title": "Evidence-Based Scientific Question Discovery: A Framework with Historical Backtesting",
             "url": "https://arxiv.org/abs/2608.09968"},
            {"title": "Historical Backtesting for Scientific Question Discovery: A Protocol and Astronomy Pilot",
             "url": "https://arxiv.org/abs/2608.16795"},
            {"title": "What Makes a Scientific Question Succeed? Predicting Future Attention, Resolution, and "
                      "Premise Revision from Question Structure and Evidence Context",
             "url": "https://openfindings.org/papers/or:2026:3eab2db2"},
            {"title": "Planning the Next Evidence Acquisition Step: An Offline Framework for Active Scientific "
                      "Discovery", "url": "https://openfindings.org/papers/or:2026:f35059ae"},
            {"doi": "10.1038/s41586-019-1335-8"}, {"doi": "10.1073/pnas.1914370116"},
            {"doi": "10.1038/s42256-023-00735-0"}, {"doi": "10.1126/science.aal4217"},
            {"doi": "10.1126/science.1237825"}, {"doi": "10.1038/s41562-023-01648-z"},
            {"doi": "10.1073/pnas.1708274114"}, {"url": "https://arxiv.org/abs/2409.04109"},
            {"url": "https://arxiv.org/abs/2306.05685"},
        ],
    }
    out = ROOT / "paper" / "openfindings_submission.json"
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False))
    print(f"wrote {out}: abstract {len(record['abstract'])} chars, body {len(record['body_markdown'])} chars, "
          f"methods {len(record['methods'])}, results {len(record['results'])}, conclusions {len(record['conclusions'])}")


if __name__ == "__main__":
    main()
