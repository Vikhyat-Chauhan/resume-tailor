# resume-tailor

> CLI tool that rewrites your resume's **Summary** and **Skills** sections for any job posting in ~20 seconds — without touching the rest of your resume.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![LiteLLM](https://img.shields.io/badge/LiteLLM-provider--agnostic-412991?style=flat)
![Playwright](https://img.shields.io/badge/Playwright-JS%20fallback-45ba4b?style=flat&logo=playwright&logoColor=white)
![LaTeX](https://img.shields.io/badge/LaTeX-PDF-008080?style=flat&logo=latex&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?style=flat&logo=pydantic&logoColor=white)

---

## Architecture

```mermaid
flowchart LR
    A([Job URL]) --> B[jd_parser\nhttpx → Playwright fallback]
    B --> C1[tailor_agent\nSummary call]
    B --> C2[tailor_agent\nSkills call]
    D([master_resume.json]) --> C1 & C2
    C1 & C2 --> E[TailoredOutput\nsummary · skills]
    E --> F[resume_builder\n{{SUMMARY}} + {{SKILLS}} → pdflatex]
    F --> G([outputs/company_role_date.pdf])
    C1 & C2 --> H([outputs/tailor.log\ntokens · cost per call])
```

---

## Quick Start

```bash
git clone https://github.com/vikhyat/resume-tailor.git && cd resume-tailor
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env          # set LLM_API_KEY and LLM_MODEL
# add {{SUMMARY}} and {{SKILLS}} into templates/resume.tex

tailor run --jd-url "https://jobs.lever.co/..." --company openai --role "mle"
# → outputs/openai_mle_2026-05-22.pdf
```

For JS-rendered job boards (Workday, Greenhouse — auto-detected):
```bash
pip install -e ".[js]" && playwright install chromium
```

---

## How It Works

Two separate LLM calls run sequentially, each with a focused prompt and a forced tool call for guaranteed structured output:

**Call 1 — Summary** (`output_summary` tool)
- Persona: experienced AI engineer actively job searching
- Rules: answer what makes you unique, what role you want, what you'll do for them; ≤ 60 words

**Call 2 — Skills** (`output_skills` tool)
- Persona: AI/ML engineer tailoring for ATS
- Rules: mirror JD keywords verbatim, 12–20 skills total, 3–5 categories ordered by JD relevance, most critical category first

Both calls receive the full `master_resume.json` + scraped JD text. Forced tool calling (not prompt instructions) ensures the response is always valid structured JSON — the model cannot return free text.

---

## Provider Setup

Switch providers by changing `.env` — no code changes needed:

```env
# OpenAI
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o

# Anthropic
LLM_API_KEY=sk-ant-...
LLM_MODEL=anthropic/claude-sonnet-4-5

# Ollama (local, no key needed)
LLM_MODEL=ollama/llama3.1
```

> Ollama requires tool-calling support. `llama3.1`, `mistral-nemo`, `qwen2.5` work. Others may not.

---

## Results

| Metric | Value |
|---|---|
| Tokens per run (gpt-4o, 2 calls) | ~9,000 in / ~200 out |
| Cost per run (gpt-4o) | ~$0.018–$0.025 |
| Static page fetch | < 1s |
| JS-rendered page fetch (Playwright) | ~5–10s |
| End-to-end wall time (fetch → PDF) | ~20–30s |
| Providers tested | OpenAI `gpt-4o`, Anthropic `claude-sonnet-4-5` |
| Job boards tested | LinkedIn (static), GE HealthCare Workday (Playwright) |

---

## Usage

```bash
# Tailor and compile PDF
tailor run --jd-url "https://careers.company.com/job/123" --company "Stripe" --role "ML Engineer"

# Dry run — print output without generating a PDF
tailor run --jd-url "..." --company nvidia --role "mle" --dry-run

# View run history with per-run cost and cumulative total
tailor history
tailor history --limit 5
```

**Example output:**
```
Fetching JD from https://...
Tailoring resume...

=== SUMMARY ===
As a skilled AI engineer with deep expertise in C++ and medical imaging, I offer a proven
track record of modernizing legacy systems. Seeking a Senior Software Engineer role to lead
development of scalable ultrasound software at GE Healthcare.

=== SKILLS ===
  Languages/Systems: C++, CUDA, HLSL, Python, Git, Linux
  Image Processing: Image Processing, Modular Architecture, Performance Optimization
  Testing/Verification: Google Test (gtest), Google Mock (gmock), Unit Testing
  Agile: Object-Oriented Design, Agile Scrum, SDLC Standards, Medical Device Standards

Tokens : 9072 in / 196 out / 9268 total
Cost   : $0.021120
Saved  : outputs/GE HealthCare_Senior Software Engineer_2026-05-22.pdf
```

**`tailor history`:**
```
DATE         COMPANY            ROLE               MODEL           TOKENS       COST  FILE
------------------------------------------------------------------------------------------------------
2026-05-22   GE HealthCare      Senior SWE         gpt-4o            9268  $0.021120  outputs/...pdf
2026-05-22   nvidia             mle                gpt-4o            9072  $0.018318  (dry run)
------------------------------------------------------------------------------------------------------
Total cost                                                    $0.039438
```

---

## Project Structure

```
resume-tailor/
├── .env.example
├── pyproject.toml
├── templates/
│   └── resume.tex                # Your LaTeX template — add {{SUMMARY}} and {{SKILLS}}
├── data/
│   └── master_resume.json        # Source of truth: experience, projects, education, skills
├── outputs/                      # Git-ignored
│   ├── tailor.log                # Rotating log: timestamp, tokens, cost per run
│   └── .run_log.jsonl            # Machine-readable run history (used by tailor history)
└── src/resume_tailor/
    ├── cli.py                    # tailor run · tailor history
    ├── jd_parser.py              # httpx fetch + Playwright fallback
    ├── tailor_agent.py           # Two LiteLLM calls + TailorResult (tokens + cost)
    ├── resume_builder.py         # LaTeX slot injection + pdflatex compile
    ├── models.py                 # Pydantic models: MasterResume, TailoredOutput, Settings
    └── log.py                    # Rotating file logger → outputs/tailor.log
```

---

## What I Learned

Using **forced tool calling** for both LLM calls — rather than prompt-instructed JSON — eliminated an entire class of parsing failures: the model fills structured arguments, not text, so markdown fences, stray commentary, and malformed JSON are impossible at the protocol level. Splitting into **two focused calls** (one per output) produced sharper results than a single combined prompt, because each call has a single persona and a single set of rules with no competing objectives. Choosing **LiteLLM** over a provider-specific SDK meant the entire provider surface — OpenAI, Anthropic, local Ollama — collapses to a single `.env` change, with cost tracking working identically across all of them via `response._hidden_params["response_cost"]`.
