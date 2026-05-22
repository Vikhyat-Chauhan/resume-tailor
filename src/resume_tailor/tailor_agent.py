import json
from dataclasses import dataclass

import litellm

from .models import MasterResume, TailoredOutput

litellm.suppress_debug_info = True

_SUMMARY_SYSTEM = (
    "You are a professional and experienced AI engineer looking for a job "
    "with the following resume."
)

_SUMMARY_USER = """\
{resume}

Action: Generate a new summary for your resume based on this JD

[JD]
{jd}

Rules:
- What is special about you that they should hire you over and above other candidates?
- What are you looking for? (job title)
- What are you going to do for them? (Unique selling proposition)
- Keep the summary under 60 words
"""

_SKILLS_SYSTEM = (
    "You are a professional AI/ML engineer actively job searching. "
    "You have the following resume."
)

_SKILLS_USER = """\
{resume}

Action: Generate a tailored Technical Skills section for the resume above, optimized for the following JD.

[JD]
{jd}

Rules:
1. Identity: Determine the correct role identity from the JD (ML Engineer vs AI Engineer vs MLOps vs SWE) \
and frame the skills section accordingly — do not mix signals.
2. Keyword mirroring: Use the JD's exact wording verbatim (e.g. if JD says "LangChain," write "LangChain" \
— not "LLM orchestration framework"). Spell out abbreviations once on first use: \
"Retrieval-Augmented Generation (RAG)".
3. ATS sizing: Include 12–20 skills total across all categories.
4. Category structure: Group into 3–5 functional subcategories (e.g. Languages, ML/AI, Infra, Tools). \
Order categories so the most JD-critical category appears first. Within each category, list the most \
JD-relevant skill first.
"""

_SUMMARY_TOOL = {
    "type": "function",
    "function": {
        "name": "output_summary",
        "description": "Output the tailored resume summary.",
        "parameters": {
            "type": "object",
            "properties": {"summary": {"type": "string"}},
            "required": ["summary"],
        },
    },
}

_SKILLS_TOOL = {
    "type": "function",
    "function": {
        "name": "output_skills",
        "description": (
            "Output the tailored skills section as an ordered list of category objects. "
            "Each object has exactly one key (the category name) whose value is a single "
            "comma-separated string of skills — not an array."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "skills": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                },
            },
            "required": ["skills"],
        },
    },
}


@dataclass
class _LLMConfig:
    model: str
    api_key: str | None
    base_url: str | None


@dataclass
class _CallResult:
    arguments: dict
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float


@dataclass
class TailorResult:
    output: TailoredOutput
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float


def _call(system: str, user: str, tool: dict, cfg: _LLMConfig) -> _CallResult:
    response = litellm.completion(
        model=cfg.model,
        api_key=cfg.api_key,
        api_base=cfg.base_url,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        tools=[tool],
        tool_choice={"type": "function", "function": {"name": tool["function"]["name"]}},
    )
    tool_call = response.choices[0].message.tool_calls[0]
    usage = response.usage
    return _CallResult(
        arguments=json.loads(tool_call.function.arguments),
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,
        cost_usd=response._hidden_params.get("response_cost") or 0.0,
    )


def tailor_resume(
    jd_text: str,
    master_resume: MasterResume,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str = "gpt-4o",
) -> TailorResult:
    cfg = _LLMConfig(model=model, api_key=api_key, base_url=base_url)
    resume_json = master_resume.model_dump_json(indent=2)

    summary_r = _call(_SUMMARY_SYSTEM, _SUMMARY_USER.format(resume=resume_json, jd=jd_text), _SUMMARY_TOOL, cfg)
    skills_r = _call(_SKILLS_SYSTEM, _SKILLS_USER.format(resume=resume_json, jd=jd_text), _SKILLS_TOOL, cfg)

    # coerce list values → comma-separated strings in case model ignores the schema
    skills = [
        {k: ", ".join(v) if isinstance(v, list) else v for k, v in entry.items()}
        for entry in skills_r.arguments["skills"]
    ]

    return TailorResult(
        output=TailoredOutput(summary=summary_r.arguments["summary"], skills=skills),
        prompt_tokens=summary_r.prompt_tokens + skills_r.prompt_tokens,
        completion_tokens=summary_r.completion_tokens + skills_r.completion_tokens,
        total_tokens=summary_r.total_tokens + skills_r.total_tokens,
        cost_usd=summary_r.cost_usd + skills_r.cost_usd,
    )
