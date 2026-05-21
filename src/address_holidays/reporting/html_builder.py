from __future__ import annotations

from pathlib import Path
from typing import Tuple
from shutil import copyfile

import markdown  # ensure 'markdown' is in requirements.txt

# Repo root: .../src/address_holidays/reporting/html_builder.py -> parents[3] = project root
BASE_DIR = Path(__file__).resolve().parents[3]
CSS_SOURCE = BASE_DIR / "docs" / "report.css"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="stylesheet" href="report.css" />
</head>
<body>
  <div class="report-container">
    {content}
  </div>
</body>
</html>
"""


def build_html_and_pdf(
    md_path: Path,
    out_dir: Path,
    title: str = "Public Holiday Compliance Review",
) -> Tuple[Path, Path | None]:
    """
    Convert a Markdown report to styled HTML, and best-effort PDF using WeasyPrint.

    Returns (html_path, pdf_path_or_None).

    NOTE: This now uses the shared docs/report.css so it matches the
    other payroll reports visually.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    if not md_path.exists():
        raise FileNotFoundError(f"Markdown report not found: {md_path}")

    md_text = md_path.read_text(encoding="utf-8")
    body_html = markdown.markdown(
        md_text,
        extensions=["extra", "tables", "fenced_code"],
    )

    full_html = HTML_TEMPLATE.format(title=title, content=body_html)

    html_path = out_dir / "report.html"
    html_path.write_text(full_html, encoding="utf-8")

    # Copy shared CSS alongside the HTML so <link href="report.css"> works
    if CSS_SOURCE.exists():
        css_target = out_dir / CSS_SOURCE.name
        try:
            copyfile(CSS_SOURCE, css_target)
        except OSError:
            # Non-fatal: HTML will still work, just without custom styling
            pass

    # Best-effort PDF via WeasyPrint
    pdf_path: Path | None = None
    try:
        from weasyprint import HTML as WPHTML  # type: ignore

        pdf_path = out_dir / "report.pdf"
        WPHTML(filename=str(html_path)).write_pdf(str(pdf_path))
    except Exception:
        # PDF generation is optional; swallow any errors.
        pdf_path = None

    return html_path, pdf_path
