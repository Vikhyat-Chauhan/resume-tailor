import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from .models import TailoredOutput

_TEMPLATE_PATH = Path("templates/resume.tex")


def _render_skills(skills: list[dict[str, str]]) -> str:
    lines = ["\\begin{itemize}"]
    for entry in skills:
        for category, items in entry.items():
            label = category.replace("&", "\\&")
            lines.append(f"    \\item \\textbf{{{label}}}: {items}")
    lines.append("\\end{itemize}")
    return "\n".join(lines)


def build_pdf(result: TailoredOutput, company: str, role: str, output_dir: str, latex_cmd: str) -> Path:
    template = _TEMPLATE_PATH.read_text()
    filled = template.replace("{{SUMMARY}}", result.summary).replace("{{SKILLS}}", _render_skills(result.skills))

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{company}_{role}_{date.today().isoformat()}"
    out_pdf = out_dir / f"{stem}.pdf"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tex_file = tmp_path / f"{stem}.tex"
        tex_file.write_text(filled)

        proc = subprocess.run(
            [latex_cmd, "-interaction=nonstopmode", "-output-directory", tmp, str(tex_file)],
            capture_output=True,
            text=True,
        )

        compiled_pdf = tmp_path / f"{stem}.pdf"
        if not compiled_pdf.exists():
            raise RuntimeError(
                f"{latex_cmd} failed.\n\nSTDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}"
            )

        shutil.copy(compiled_pdf, out_pdf)

    return out_pdf
