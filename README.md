# VIPS FAQ Bot

A chatbot that answers student questions about Vivekananda Institute of Professional Studies (VIPS) using a fixed knowledge base. It covers attendance, exams, timetable, hostel, canteen, library and fees, and says so when it doesn't have the information.

**Live demo:** [add link after deployment]

## Model and design

- **Model:** Gemini (`gemini-3.1-flash-lite`) through the `google-genai` SDK, temperature 0.
- **Backend:** FastAPI with `POST /ask` and `GET /health`.
- **Frontend:** a static chat page. The typing effect is a client-side reveal, not streaming.
- **Reliability:** retry with optional model fallback (several models can be listed in `MODELS`).

## Run it locally

```bash
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Put your key in `.env` (see `.env.example`). Run the tests with `python -m pytest -v`. There are 20 tests, and Gemini is mocked, so no key is needed.

## Evaluation

58 questions in 6 categories, scored by keyword match. I compared three prompt versions on one model:

```bash
python eval/run_eval.py v1 v2 v3
```

| Category | v1 | v2 | v3 |
|---|---|---|---|
| normal | 14/14 | 14/14 | 14/14 |
| typo_casual | 10/10 | 10/10 | 10/10 |
| out_of_scope | 8/8 | 8/8 | 8/8 |
| partial | 2/2 | 2/2 | 2/2 |
| tricky | 14/14 | 13/14 | 14/14 |
| held_out | 10/10 | 10/10 | 10/10 |
| **Total** | **58/58** | **57/58** | **58/58** |

What reading the answers showed:

- **v1 (original):** played along with a "pretend you're the principal" request and mentioned a "student portal" that isn't in the knowledge base.
- **v2 (strict):** gave the generic fallback on the hostel fee question, although the knowledge base says there is no hostel.
- **v3 (final):** declined the role-play, answered "no hostel" directly, and didn't invent details.

The scores can't separate the prompts, because the gaps are one question out of 58. The real finding came from reading the answers: a stricter prompt can look clean and still answer worse, and keyword scoring missed the loosest prompt's role-play.

I wrote v3 after seeing v2's failure, then checked it on 10 held-out questions I had written beforehand. All three prompts scored 10/10 on them, so this shows v3 didn't regress, not that it improved.

## Limitations

- One model and one run per prompt.
- Keyword scoring only. A refusal case passes if any of 14 phrases appears, and other cases check only for required keywords. Neither penalises extra invented content, so the scorer passed v1's role-play answer ("As the principal..."), which I only caught by reading the answers.
- I wrote the test questions myself.
- I widened the scorer after seeing early results. The model words "I don't know" in many ways ("I do not have information", "does not contain", "I can only help with questions about VIPS"), so a short list of phrases marked correct refusals as failures. I added phrases until correct refusals passed. The scores shouldn't be treated as a clean benchmark.
- In live use, "tell me about the VIPS" produced a claim the knowledge base doesn't state ("offers various academic programs"). I left the prompt unchanged, and this question belongs in a future evaluation set.
- The open/closed status in the page header is hardcoded from the knowledge base hours.