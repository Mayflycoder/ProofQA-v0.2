"""Portable, escaped HTML and JSON evidence reports."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

from pqlqa.models import Report


def write_report(report: Report, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output / "report.html").write_text(render_html(report), encoding="utf-8")
    (output / "report.md").write_text(render_markdown(report), encoding="utf-8")


def render_html(report: Report) -> str:
    def e(text: object) -> str:
        return html.escape(str(text), quote=True)
    counts = report.to_dict()["counts"]
    rows = "\n".join(
        "<tr>" + "".join(f"<td>{e(value)}</td>" for value in (
            check.page_path, check.viewport, check.check_id, check.status,
            check.finding, check.expected, check.observed,
        )) + "</tr>" for check in report.checks
    )
    images = "\n".join(
        f'<figure><img src="{e(filename)}" alt="{e(viewport)} screenshot" />'
        f'<figcaption>{e(viewport)}</figcaption></figure>'
        for viewport, filename in report.screenshots.items()
    )
    limitations = "".join(f"<li>{e(item)}</li>" for item in report.limitations)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ProofQA — {e(report.run_id)}</title>
<style>
:root {{font:15px/1.55 system-ui,sans-serif;color:#162b38;background:#eff4f6}}
body {{max-width:1100px;margin:24px auto;padding:0 18px}}
main {{background:white;padding:26px;border-radius:16px;box-shadow:0 8px 32px #18364b15}}
h1 {{margin:0}} small {{color:#55707c}}
.summary {{display:flex;gap:12px;flex-wrap:wrap;margin:22px 0}}
.summary span {{padding:10px 17px;background:#edf5f5;border-radius:8px;font-weight:650}}
.table-scroll {{overflow-x:auto}} table {{width:100%;border-collapse:collapse;font-size:13px}}
tr {{border-bottom:1px solid #dae3e7}} td,th {{padding:10px;text-align:left;vertical-align:top}}
th {{background:#eff4f6}}
figure {{display:inline-block;max-width:45%;vertical-align:top;margin:12px}}
img {{display:block;max-width:100%;border:1px solid #dae3e7}}
.caveat {{background:#f5f8fa;padding:15px;border-radius:8px}}
@media(max-width:650px) {{main {{padding:16px}} figure {{max-width:100%;margin:12px 0}}}}
</style></head><body><main>
<small>ProofQA / Local smoke test / Not a release certification</small>
<h1>QA run {e(report.run_id)}</h1><p><strong>Target:</strong> {e(report.target)}<br>
<strong>UTC timestamp:</strong> {e(report.created_at)}</p>
<div class="summary">{''.join(f'<span>{e(k)}: {v}</span>' for k,v in counts.items())}</div>
<p>{e(report.scope)}</p><h2>Results</h2>
<div class="table-scroll"><table><thead>
<tr><th>Page</th><th>Viewport</th><th>ID</th><th>Status</th><th>Check</th>
<th>Expected</th><th>Observed</th></tr></thead><tbody>{rows}</tbody></table></div>
<h2>Evidence: screenshots</h2>{images or '<p>No screenshots available.</p>'}
<section class="caveat"><h2>Scope limitations</h2><ul>{limitations}</ul>
<p><strong>Not a regulatory approval, security audit, or proof of complete functionality.
</strong></p></section>
</main></body></html>"""



def render_markdown(report: Report) -> str:
    """Generate a portable Markdown summary, escaping untrusted observations."""
    def cell(value: object) -> str:
        clean = html.escape(str(value), quote=True)
        clean = clean.replace("\n", " ").replace("\r", " ")
        # Do not activate Markdown links, images, HTML or table breakouts.
        return re.sub(r"([\\`*_{}\[\]()#+.!|>~])", r"\\\1", clean)

    counts = report.to_dict()["counts"]
    lines = [
        f"# ProofQA run {cell(report.run_id)}",
        "",
        f"Target: {cell(report.target)}",
        "",
        f"Timestamp (UTC): {cell(report.created_at)}",
        "",
        " ".join(f"**{key}: {value}**" for key, value in counts.items()),
        "",
        cell(report.scope),
        "",
        "| Page | Viewport | Check | Status | Expected | Observed |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for check in report.checks:
        lines.append(
            f"| {cell(check.page_path)} | {cell(check.viewport)} "
            f"| {cell(check.check_id)} | {check.status} "
            f"| {cell(check.expected)} | {cell(check.observed)} |"
        )
    lines.extend(["", "## Screenshot evidence", ""])
    if report.screenshots:
        for viewport, filename in report.screenshots.items():
            lines.append(f"- {cell(viewport)}: ![{cell(viewport)} screenshot]({cell(filename)})")
    else:
        lines.append("No screenshots available.")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {cell(item)}" for item in report.limitations)
    lines.append("")
    lines.append("**Not a security audit, regulatory approval, or release certification.**")
    lines.append("")
    return "\n".join(lines)
