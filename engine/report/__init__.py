"""Report outputs: analysis.json / metrics.csv (core), report.html and compare.html (html), analysis.xlsx (xlsx).

All text comes from deterministic templates in engine/report/templates/.
"""
from .core import (_clean, build_report, console_summary, fmt, metric_text, metrics_frame, out_dir_for,  # noqa: F401
                   write_outputs)
