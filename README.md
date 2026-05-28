# ECS_189G_WallStreetBench

for chatgpt runing:
run in separate chats outside a project &&
delete the chat after runing

annotation google sheet:
https://docs.google.com/spreadsheets/d/1-ojP69q-7EARw5LCVN6V4UGaIrcvAtY5ABqbZWeRRUM/edit?usp=sharing

## Annotation CSV Schema

One row per (response × annotator). A response double-annotated by two people = 2 rows.

| Column | Type | Values | Description |
|---|---|---|---|
| `prompt_id` | string | e.g. `C1-P1`, `C1-P1.v1`, `C5-P3` | Matches the IDs in `189G_prompts.docx` |
| `category` | string | `C1`–`C5` | Content category |
| `model` | string | `Qwen3-0.6B` / `DeepSeek-V4-Pro` / `ChatGPT-Plus` | Which model produced the response |
| `annotator` | string | `A1`–`A4` | Who scored it |
| `is_double` | int | `0` or `1` | `1` = this row is the second annotator on a double-annotated item |
| `turn_index` | int | `0`, `1`, `2`, ... | `0` = base prompt, `1+` = follow-up turns |
| `reasoning_quality` | int | `1`–`5` | Rubric §3.1 |
| `err_hallucination` | int | `0`–`3` | Count of hallucinated facts (cap at 3) |
| `err_misinterpretation` | int | `0`–`3` | Count of misread data points |
| `err_overconfidence` | int | `0`–`3` | Count of unsupported confident claims |
| `err_contradiction` | int | `0`–`3` | Count of internal contradictions |
| `uncertainty` | int | `1`–`3` | Rubric §3.3 |
| `risk_awareness` | int | `1`–`3` | Rubric §3.4 |
| `tradeoff` | string | `Yes` / `No` | Rubric §3.5 |
| `consistency_group` | string | e.g. `C1-P1-group` or empty | Groups together prompts that should give consistent answers (original + .v1 + .v2) |
| `notes` | string | free text | One-line annotator comment, useful for case study analysis |

## Rules

1. **Every base prompt** gets `turn_index=0`. Each follow-up = next index. The follow-ups inherit the same `prompt_id`.
2. **Primary annotation**: `is_double=0`. **Double annotation**: `is_double=1`. The notebook uses this flag to compute inter-rater reliability and to pick which row to keep for aggregation (it averages the two scores after adjudication).
3. **Consistency groups** only matter for prompts that have `.v1` / `.v2` variants. Leave blank otherwise.
4. **Error counts**: count distinct instances. Cap at 3.
5. **De-identification during annotation**: rename the response files so the annotator does not see which model produced them. The mapping is restored at analysis time.
