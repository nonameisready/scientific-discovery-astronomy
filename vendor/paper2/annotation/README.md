# Blinded annotation package

**Do not open `decode.json` until both annotation sheets are complete.**
It maps the anonymised system codes back to real systems, and reading it
before annotating destroys the blinding this validation depends on.

## Files

| File | What to do with it |
|---|---|
| `codebook.md` | Read first, in full. |
| `annotation_packet.md` | The 90 items, in fixed order. Read here. |
| `annotator_1_sheet.csv`, `annotator_2_sheet.csv` | One per person. Fill `outcome`, `premise_status`, `confidence`, `notes`. |
| `decode.json` | Sealed until both sheets are done. |

## Steps

1. Two people read `codebook.md`.
2. Each fills their own sheet independently, no discussion.
3. Run `python scripts/human_annotation.py score`, which reports
   human-human agreement and human-LLM agreement.
4. Meet, resolve disagreements, and record the reasoning in the
   `notes` column of a merged sheet named `adjudicated_sheet.csv`
   (same columns). This becomes the released adjudication log.

If only one annotator is available the package still works: you get
human-LLM agreement but no human-human ceiling, and the paper must say so.
