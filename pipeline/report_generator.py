"""report_generator.py - Stage 6 - HTML report for GitHub Pages."""

import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ReportGenerator:
      def __init__(self, output_dir="./docs"):
                self.output_dir = Path(output_dir)
                self.output_dir.mkdir(parents=True, exist_ok=True)

      def generate(self, meta, static_report, complexity_report,
                                    refactoring_report, benchmark_report):
                                              now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                                              html = self._html(meta, static_report, complexity_report,
                                                                refactoring_report, benchmark_report, now)
                                              out = self.output_dir / "index.html"
                                              out.write_text(html, encoding="utf-8")
                                              logger.info("Report: %s", out)
                                              return str(out)

      def _html(self, m, st, cx, rf, bk, now):
                css = (
                              ":root{--bg:#0d1117;--sf:#161b22;--bd:#30363d;"
                              "--tx:#c9d1d9;--mu:#8b949e;--ac:#58a6ff;"
                              "--gr:#3fb950;--ye:#d29922;--re:#f85149}"
                              "*{box-sizing:border-box;margin:0;padding:0}"
                              "body{background:var(--bg);color:var(--tx);"
                              "font-family:system-ui,sans-serif;padding:2rem}"
                              "h1{color:var(--ac);margin-bottom:.5rem}"
                              "h2{color:var(--tx);border-bottom:1px solid var(--bd);"
                              "padding-bottom:.4rem;margin:2rem 0 1rem}"
                              ".meta{color:var(--mu);font-size:.9rem;margin-bottom:2rem}"
                              ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));"
                              "gap:1rem;margin-bottom:2rem}"
                              ".card{background:var(--sf);border:1px solid var(--bd);"
                              "border-radius:8px;padding:1.2rem;text-align:center}"
                              ".val{font-size:2rem;font-weight:700;color:var(--ac)}"
                              ".lbl{color:var(--mu);font-size:.85rem;margin-top:.3rem}"
                              "table{width:100%;border-collapse:collapse;font-size:.85rem}"
                              "th,td{padding:.5rem .75rem;border:1px solid var(--bd);text-align:left}"
                              "th{background:var(--sf);color:var(--ac)}"
                              "tr:nth-child(even){background:var(--sf)}"
                              ".pill{display:inline-block;padding:.1rem .5rem;border-radius:4px;"
                              "font-size:.75rem;font-weight:600}"
                              ".pr{background:#f8514930;color:var(--re)}"
                              ".py{background:#d2992230;color:var(--ye)}"
                              ".pg{background:#3fb95030;color:var(--gr)}"
                              ".rc{background:var(--sf);border:1px solid var(--bd);"
                              "border-radius:8px;padding:1rem;margin-bottom:1rem}"
                              ".rc h3{color:var(--ac);font-size:1rem;margin-bottom:.5rem}"
                              "ul{padding-left:1.5rem} li{margin:.25rem 0}"
                              "footer{color:var(--mu);text-align:center;margin-top:3rem;font-size:.8rem}"
                )
                smells = "".join(f"<li>{s}</li>" for s in cx.smells) or "<li>None.</li>"
                suggs  = "".join(f"<li>{s}</li>" for s in rf.structural_suggestions) or "<li>None.</li>"

          issues = ""
        for i in st.issues[:50]:
                      pc = "pr" if i.severity == "error" else "py"
                      issues += (f"<tr><td>{i.file}:{i.line}</td>"
                                 f"<td><span class='pill {pc}'>{i.severity}</span></td>"
                                 f"<td>{i.code}</td><td>{i.message}</td><td>{i.tool}</td></tr>")
                  if not issues:
                                issues_sec = "<p>No issues found.</p>"
else:
            issues_sec = (
                              "<table><thead><tr><th>Location</th><th>Severity</th>"
                              "<th>Code</th><th>Message</th><th>Tool</th></tr></thead>"
                              f"<tbody>{issues}</tbody></table>"
            )

        cards = ""
        for r in rf.results:
                      imps = "".join(f"<li>{i}</li>" for i in r.improvements)
                      cards += (f"<div class='rc'><h3>{r.original_function}() - {r.original_file}</h3>"
                                f"<p><em>{r.rationale}</em></p><ul>{imps}</ul></div>")
                  if not cards:
                                cards = "<p>No refactoring suggestions (no smells found or LLM not configured).</p>"

        brows = ""
        for r in bk.results:
                      pc = "pg" if r.speedup_ratio >= 1.1 else "py"
                      brows += (f"<tr><td>{r.function_name}</td><td>{r.file}</td>"
                                f"<td>{r.original_time_ms:.4f}ms</td>"
                                f"<td>{r.refactored_time_ms:.4f}ms</td>"
                                f"<td><span class='pill {pc}'>{r.speedup_ratio:.2f}x</span></td>"
                                f"<td>{r.memory_delta_kb:.2f}KB</td></tr>")
                  if not brows:
                                bench_sec = "<p>No benchmarks available.</p>"
else:
            bench_sec = (
                              "<table><thead><tr><th>Function</th><th>File</th>"
                              "<th>Original</th><th>Refactored</th><th>Speedup</th><th>Mem Saved</th></tr></thead>"
                              f"<tbody>{brows}</tbody></table>"
            )

        return (
                      "<!DOCTYPE html><html lang='en'><head>"
                      f"<meta charset='UTF-8'><title>Refactoring Report - {m.name}</title>"
                      f"<style>{css}</style></head><body>"
                      "<h1>AI Code Refactoring Report</h1>"
                      f"<p class='meta'>Repo: <b>{m.url}</b> | Branch: {m.branch} | {now}</p>"
                      "<div class='grid'>"
                      f"<div class='card'><div class='val'>{m.file_count}</div><div class='lbl'>Files</div></div>"
                      f"<div class='card'><div class='val'>{m.total_lines:,}</div><div class='lbl'>Lines</div></div>"
                      f"<div class='card'><div class='val'>{st.score:.1f}/10</div><div class='lbl'>Static Score</div></div>"
                      f"<div class='card'><div class='val'>{cx.maintainability_score:.0f}/100</div><div class='lbl'>Maintainability</div></div>"
                      f"<div class='card'><div class='val'>{bk.overall_speedup:.2f}x</div><div class='lbl'>Speedup</div></div>"
                      f"<div class='card'><div class='val'>{len(cx.smells)}</div><div class='lbl'>Smells</div></div>"
                      "</div>"
                      "<h2>Static Analysis</h2>" + issues_sec +
                      f"<h2>Code Smells</h2><ul>{smells}</ul>"
                      f"<h2>Structural Suggestions</h2><ul>{suggs}</ul>"
                      "<h2>Refactoring Suggestions</h2>" + cards +
                      "<h2>Benchmarks</h2>" + bench_sec +
                      f"<footer>Generated by AI Code Refactoring System - {now}</footer>"
                      "</body></html>"
        )
