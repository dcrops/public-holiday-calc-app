from __future__ import annotations

from pathlib import Path
from typing import Tuple

import markdown  # ensure 'markdown' is in requirements.txt


BASE_CSS = """
body {
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 14px;
    line-height: 1.5;
    color: #222;
    margin: 0;
    padding: 2rem;
    background: #f5f5f5;
}

.report-container {
    max-width: 900px;
    margin: 0 auto;
    background: #fff;
    padding: 2rem 2.5rem;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

h1, h2, h3, h4 {
    font-weight: 600;
    color: #111827;
}

h1 {
    font-size: 1.8rem;
    margin-bottom: 0.75rem;
}

h2 {
    font-size: 1.4rem;
    margin-top: 2rem;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 0.25rem;
}

h3 {
    font-size: 1.1rem;
    margin-top: 1.25rem;
}

code {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 0.9em;
    background: #f3f4f6;
    padding: 0.1em 0.3em;
    border-radius: 4px;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 0.75rem 0;
    font-size: 0.9rem;
}

th, td {
    border: 1px solid #e5e7eb;
    padding: 0.4rem 0.5rem;
    text-align: left;
}

th {
    background: #f9fafb;
    font-weight: 600;
}

blockquote {
    border-left: 4px solid #e5e7eb;
    margin: 0.75rem 0;
    padding: 0.5rem 0.75rem;
    color: #4b5563;
    background: #f9fafb;
}

hr {
    border: none;
    border-top: 1px solid #e5e7eb;
    margin: 2rem 0 1.5rem;
}
"""


def build_html_and_pdf(
    md_path: Path,
    out_dir: Path,
    title: str = "Compliance Report",
) -> Tuple[Path, Path | None]:
    """
    Convert a Markdown report to styled HTML, and best-effort PDF using WeasyPrint.

    Returns (html_path, pdf_path_or_None).
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    md_text = md_path.read_text(encoding="utf-8")
    body_html = markdown.markdown(md_text, extensions=["tables", "fenced_code"])

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
  {BASE_CSS}
  </style>
</head>
<body>
  <div class="report-container">
    {body_html}
  </div>
</body>
</html>
"""

    html_path = out_dir / "report.html"
    html_path.write_text(html_doc, encoding="utf-8")

    # Best-effort PDF via WeasyPrint
    pdf_path: Path | None = None
    try:
        from weasyprint import HTML  # type: ignore

        pdf_path = out_dir / "report.pdf"
        HTML(string=html_doc, base_url=str(out_dir)).write_pdf(str(pdf_path))
    except Exception:
        # PDF generation is optional; swallow any errors.
        pdf_path = None

    return html_path, pdf_path
