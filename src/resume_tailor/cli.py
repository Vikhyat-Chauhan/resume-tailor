import json
import os
from datetime import datetime, timezone
from pathlib import Path

import typer
from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault("LITELLM_LOG", "ERROR")

from .jd_parser import fetch_jd
from .log import get_logger
from .models import MasterResume, Settings
from .resume_builder import build_pdf
from .tailor_agent import tailor_resume

app = typer.Typer(help="Tailor your resume for a specific job description.", no_args_is_help=True)

_RESUME_PATH = Path("data/master_resume.json")
_RUN_LOG = Path("outputs/.run_log.jsonl")


def _load_master_resume() -> MasterResume:
    if not _RESUME_PATH.exists():
        typer.echo(
            f"Error: {_RESUME_PATH} not found. Fill in data/master_resume.json with your details.",
            err=True,
        )
        raise typer.Exit(1)
    return MasterResume.model_validate_json(_RESUME_PATH.read_text())


def _append_run(entry: dict) -> None:
    _RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    with _RUN_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")


@app.command("run")
def run(
    jd_url: str = typer.Option(..., "--jd-url", help="URL of job description"),
    company: str = typer.Option(..., "--company", help="Company name for output filename"),
    role: str = typer.Option(..., "--role", help="Role name for output filename"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print tailored sections without generating a file"),
):
    """Tailor your resume summary and skills for a specific job."""
    log = get_logger()

    settings = Settings()
    master_resume = _load_master_resume()

    typer.echo(f"Fetching JD from {jd_url}...")
    try:
        jd_text = fetch_jd(jd_url)
    except RuntimeError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    typer.echo("Tailoring resume...")
    tailor_result = tailor_resume(
        jd_text,
        master_resume,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
    )
    result = tailor_result.output

    typer.echo("\n=== SUMMARY ===")
    typer.echo(result.summary)
    typer.echo("\n=== SKILLS ===")
    for entry in result.skills:
        for category, items in entry.items():
            typer.echo(f"  {category}: {items}")
    typer.echo(
        f"\nTokens : {tailor_result.prompt_tokens} in / "
        f"{tailor_result.completion_tokens} out / "
        f"{tailor_result.total_tokens} total"
    )
    typer.echo(f"Cost   : ${tailor_result.cost_usd:.6f}")

    log.info(
        "tailored company=%s role=%s model=%s "
        "prompt_tokens=%d completion_tokens=%d total_tokens=%d cost_usd=%.6f dry_run=%s",
        company, role, settings.llm_model,
        tailor_result.prompt_tokens, tailor_result.completion_tokens,
        tailor_result.total_tokens, tailor_result.cost_usd, dry_run,
    )

    run_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "company": company,
        "role": role,
        "model": settings.llm_model,
        "jd_url": jd_url,
        "prompt_tokens": tailor_result.prompt_tokens,
        "completion_tokens": tailor_result.completion_tokens,
        "total_tokens": tailor_result.total_tokens,
        "cost_usd": tailor_result.cost_usd,
        "dry_run": dry_run,
        "output_file": None,
    }

    if not dry_run:
        try:
            out_path = build_pdf(result, company, role, settings.output_dir, settings.latex_cmd)
            typer.echo(f"Saved  : {out_path}")
            run_entry["output_file"] = str(out_path)
            log.info("pdf saved path=%s", out_path)
        except RuntimeError as e:
            typer.echo(f"\nError building PDF:\n{e}", err=True)
            log.error("pdf build failed: %s", e)
            _append_run(run_entry)
            raise typer.Exit(1)

    _append_run(run_entry)


@app.command("history")
def history(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of runs to show"),
):
    """List past tailoring runs with token usage and cost."""
    if not _RUN_LOG.exists():
        typer.echo("No runs logged yet.")
        raise typer.Exit(0)

    entries = [json.loads(line) for line in _RUN_LOG.read_text().splitlines() if line.strip()]
    entries = entries[-limit:]

    if not entries:
        typer.echo("No runs logged yet.")
        raise typer.Exit(0)

    header = f"{'DATE':<12} {'COMPANY':<18} {'ROLE':<18} {'MODEL':<14} {'TOKENS':>7}  {'COST':>9}  FILE"
    typer.echo(header)
    typer.echo("-" * (len(header) + 20))

    total_cost = 0.0
    for e in entries:
        cost = e.get("cost_usd", 0.0)
        total_cost += cost
        out = e.get("output_file") or ("(dry run)" if e.get("dry_run") else "-")
        typer.echo(
            f"{e['timestamp'][:10]:<12} "
            f"{e['company'][:17]:<18} "
            f"{e['role'][:17]:<18} "
            f"{e['model'][:13]:<14} "
            f"{e['total_tokens']:>7}  "
            f"${cost:>8.6f}  "
            f"{out}"
        )

    typer.echo("-" * (len(header) + 20))
    typer.echo(f"{'Total cost':<61} ${total_cost:.6f}")


def main():
    app()
