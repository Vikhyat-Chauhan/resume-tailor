# resume-tailor

An agentic CLI tool that rewrites your resume's **Summary** and **Skills** sections for a specific job description — without touching the rest of your resume.

---

## What It Does

1. Takes a job description (URL or pasted text) and your master resume JSON
2. Uses Claude API to generate a tailored summary and filtered/reordered skills list
3. Injects the new sections into your LaTeX or DOCX resume template
4. Saves a versioned output file per application (`company_role_YYYY-MM-DD.pdf`)

---

## Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| LLM | Claude API (`claude-sonnet-4-20250514`) |
| Resume source of truth | `master_resume.json` |
| Output formats | PDF (via LaTeX) or DOCX |
| CLI | `typer` |
| Config | `pydantic-settings` + `.env` |

---

## Project Structure

```
resume-tailor/
├── README.md
├── .env.example
├── .gitignore
├── pyproject.toml
│
├── data/
│   └── master_resume.json        # Your structured resume (source of truth)
│
├── templates/
│   ├── resume.tex                # LaTeX template with {{SUMMARY}} {{SKILLS}} slots
│   └── resume.docx               # Optional DOCX template (same slots)
│
├── outputs/                      # Git-ignored; generated files land here
│   └── amazon_sde2_2025-06-01.pdf
│
├── src/
│   └── resume_tailor/
│       ├── __init__.py
│       ├── cli.py                # typer entrypoint: `tailor run`
│       ├── jd_parser.py          # Fetch JD from URL or accept raw text
│       ├── tailor_agent.py       # Claude API call + structured output parsing
│       ├── resume_builder.py     # Injects sections into template → PDF/DOCX
│       └── models.py             # Pydantic models: TailoredOutput, MasterResume
│
└── tests/
    ├── test_tailor_agent.py
    └── fixtures/
        └── sample_jd.txt
```

---

## Data: `master_resume.json`

This is the single source of truth the agent reads from. Keep it updated.

```json
{
  "name": "Vikhyat Chauhan",
  "contact": {
    "email": "...",
    "linkedin": "linkedin.com/in/...",
    "github": "github.com/...",
    "site": "vikhyatchauhan.com"
  },
  "summary_pool": [
    "ML engineer with experience in TensorRT optimization (20% throughput improvement on Swin Transformer) and production MRI pipelines at GE HealthCare.",
    "Neuroscience-inspired autonomous systems researcher; MS thesis achieved 13.31% improvement in UAV navigation energy and elapsed time (p < 0.0001, n=1000).",
    "Full-stack ML background spanning firmware/embedded (TNM Electronics, co-inventor) through cloud ML (GCP, AWS) and LLM systems (RAG, LangGraph agents)."
  ],
  "skills": {
    "ml_frameworks": ["PyTorch", "TensorRT", "ONNX", "Hugging Face", "LangChain", "LangGraph"],
    "languages": ["Python", "C++", "C", "JavaScript", "Bash"],
    "cloud": ["AWS", "GCP Cloud Run", "Docker", "Kubernetes"],
    "tools": ["ROS 2", "Gazebo", "ChromaDB", "PostgreSQL", "Git"],
    "domains": ["Medical Imaging", "Edge AI", "Autonomous Systems", "LLM Systems", "RAG"]
  },
  "experience": [...],
  "projects": [...],
  "education": [...]
}
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/vikhyat/resume-tailor.git
cd resume-tailor
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env:
# ANTHROPIC_API_KEY=sk-ant-...
# OUTPUT_FORMAT=pdf   # or docx
```

### 3. Populate your master resume

Edit `data/master_resume.json` with your actual content.

### 4. Set up your resume template

For LaTeX: edit `templates/resume.tex` and place `{{SUMMARY}}` and `{{SKILLS}}` where those sections go.

For DOCX: place the same placeholders as plain text in `templates/resume.docx`.

---

## Usage

```bash
# Tailor from a URL
tailor run --jd-url "https://www.amazon.jobs/en/jobs/..." --company amazon --role "SDE-II"

# Tailor from pasted text
tailor run --jd-file jd.txt --company premera --role "ai-engineer-ii"

# Dry run: print tailored sections without generating a file
tailor run --jd-url "..." --company nvidia --role "mle" --dry-run
```

Output lands in `outputs/nvidia_mle_2025-06-01.pdf`.

---

## How the Agent Works

```
JD text
   │
   ▼
tailor_agent.py
   │  Prompt: "Given this JD and resume JSON, return:
   │    1. A 2-3 sentence summary (use facts from summary_pool)
   │    2. A skills list (max 5 categories, ordered by JD relevance)
   │    3. Brief rationale for each choice"
   │
   ▼
TailoredOutput (Pydantic model)
   {
     summary: str,
     skills: dict[str, list[str]],
     rationale: str
   }
   │
   ▼
resume_builder.py
   │  Replace {{SUMMARY}} and {{SKILLS}} in template
   │  Compile LaTeX → PDF  (or inject into DOCX)
   ▼
outputs/company_role_date.pdf
```

---

## Build Phases

### Phase 1 — Core tailor loop (start here)
- [ ] Define `master_resume.json` schema and fill it out
- [ ] Write `tailor_agent.py` with Claude API call and structured output
- [ ] Parse and validate `TailoredOutput` with Pydantic
- [ ] CLI: `tailor run --jd-file --dry-run` (print only)

### Phase 2 — Template injection
- [ ] LaTeX template with `{{SUMMARY}}` / `{{SKILLS}}` slots
- [ ] `resume_builder.py`: string replace → `pdflatex` compile
- [ ] Versioned output naming (`company_role_date.pdf`)

### Phase 3 — JD fetching
- [ ] `jd_parser.py`: fetch JD from URL using `httpx` + `BeautifulSoup`
- [ ] Handle Workday JD pages (JS-heavy; may need `playwright`)
- [ ] CLI flag: `--jd-url`

### Phase 4 — Polish
- [ ] DOCX output option alongside PDF
- [ ] `tailor history` command: list past outputs with metadata
- [ ] Token usage logging per run

---

## `.env.example`

```env
ANTHROPIC_API_KEY=sk-ant-...
OUTPUT_FORMAT=pdf
OUTPUT_DIR=outputs
LATEX_CMD=pdflatex
```

---

## `.gitignore`

```
.env
.venv/
outputs/
__pycache__/
*.egg-info/
dist/
data/master_resume.json   # Keep your resume out of git if repo is public
```

---

## Dependencies (`pyproject.toml`)

```toml
[project]
name = "resume-tailor"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "anthropic>=0.25.0",
    "typer>=0.12.0",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "httpx>=0.27.0",
    "beautifulsoup4>=4.12.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = ["pytest", "ruff", "mypy"]

[project.scripts]
tailor = "resume_tailor.cli:app"
```
