# Packet A: screening instructions (round 6)

Thank you for helping. Please work **independently**. Don't discuss your answers with the other screener, and don't ask the analyst about the study's hypotheses.

## Your task

`packet_A_screening.csv` lists 200 highly cited astro-ph papers (2006–2021) whose title contains a claim word: evidence, detection, excess, tension, anomaly and similar. For each row, fill in the three columns below.

| Column | What to enter |
|---|---|
| `is_contested_anomalous_claim (yes/no)` | **yes** if the paper reports, or is the origin of, a result that was anomalous or unexpected *and* that other groups went on to test, dispute or try to explain. **no** for reviews, routine measurements, method papers, expected detections, and theory papers that only propose an explanation of someone else's anomaly. |
| `key_phrase_used_by_later_papers` | Only for **yes** rows: the short name later papers use for the claim, for example "3.5 keV line" or "Planet Nine". |
| `notes` | Optional. Use it to flag duplicates of the same claim, for example "same claim as row 37". |

Two more things:

- **Don't write anything about how the claim turned out.** Outcomes are collected separately, later, in Packet B.
- **The `round5_case_flag` column** marks rows that look like claims already used in round 5. You may mark those **no**.

Rows are in citation order. If you can't judge a row from the title and abstract, write `no` and add "unsure" in `notes`.

Please return the CSV with your initials in the file name, for example `packet_A_screening_HM.csv`.
