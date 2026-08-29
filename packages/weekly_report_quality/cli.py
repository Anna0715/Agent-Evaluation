"""Weekly-report quality CLI.

Usage (from repo root):
  PYTHONPATH=packages python3 -m weekly_report_quality <command> ...
or directly:
  PYTHONPATH=packages python3 -m weekly_report_quality <command> ...

Commands:
  lint     Lint a case directory.
  import   Import legacy markdown cases into versioned JSON cases.
  run      Execute the suite offline from evidence artifacts.
  daily    Scheduled entrypoint: run + three checks + report + archive.
  report   Emit the daily comparison report across scheduled runs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages"))

from weekly_report_quality.contracts import ContractError, load_cases, write_json
from weekly_report_quality.importer import import_markdown
from weekly_report_quality.lint import lint_cases
from weekly_report_quality.report import daily_report, write_run_outputs
from weekly_report_quality.runner import RunConfig, execute_run


def _cmd_lint(args: argparse.Namespace) -> int:
    cases = load_cases(Path(args.cases))
    issues = lint_cases(cases)
    if not issues:
        print(f"OK: {len(cases)} cases passed lint")
        return 0
    for issue in issues:
        print(f"LINT {issue.case_id} [{issue.field}] {issue.message}", file=sys.stderr)
    return 1


def _cmd_import(args: argparse.Namespace) -> int:
    cases = import_markdown(Path(args.input))
    out_dir = Path(args.out_dir)
    for case in cases:
        write_json(out_dir / f"{case['id']}.json", case)
    print(f"imported {len(cases)} cases into {out_dir}")
    return 0


def _run_config(args: argparse.Namespace, trigger: str) -> RunConfig:
    return RunConfig(
        cases_dir=Path(args.cases),
        evidence_dir=Path(args.evidence),
        out_dir=Path(args.out),
        baseline_file=Path(args.baseline) if args.baseline else None,
        run_id=getattr(args, "run_id", "") or "",
        trigger=trigger,
        selected_evaluators=args.evaluators.split(",") if args.evaluators else None,
        selected_tags=args.tags.split(",") if args.tags else None,
        selected_cases=args.case.split(",") if args.case else None,
        pass_threshold=args.threshold,
        resume=getattr(args, "resume", False),
    )


def _execute_and_write(config: RunConfig, gate: bool) -> int:
    run = execute_run(config)
    paths = write_run_outputs(run, config.out_dir)
    summary = run["summary"]
    print(
        f"run {run['run_id']}: pass={summary['pass']} fail={summary['fail']} "
        f"skip={summary['skip']} error={summary['error']} "
        f"confidence={summary['confidence_distribution']}"
    )
    print(f"report: {paths['markdown']}")
    if gate and (summary["fail"] or summary["error"]):
        return 1
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    return _execute_and_write(_run_config(args, trigger="manual"), gate=args.gate)


def _cmd_daily(args: argparse.Namespace) -> int:
    """Scheduled entrypoint used by cron/Jenkins twice a day.

    Baseline defaults to the most recent archived run so baseline_check can
    compare against the previous scheduled run automatically.
    """
    out_dir = Path(args.out)
    baseline = Path(args.baseline) if args.baseline else None
    if baseline is None and out_dir.exists():
        previous = sorted(out_dir.glob("*/run.json"))
        if previous:
            baseline = previous[-1]
    config = _run_config(args, trigger="scheduled")
    config.baseline_file = baseline
    slot = dt.datetime.now().strftime("%Y%m%dT%H%M")
    config.run_id = config.run_id or f"scheduled-{slot}"
    exit_code = _execute_and_write(config, gate=False)
    date = dt.datetime.now().strftime("%Y%m%d")
    report_path = out_dir / f"daily-{date}.md"
    report_path.write_text(daily_report(out_dir, date), encoding="utf-8")
    print(f"daily report: {report_path}")
    return exit_code


def _cmd_report(args: argparse.Namespace) -> int:
    content = daily_report(Path(args.runs_dir), args.date)
    if args.out:
        Path(args.out).write_text(content, encoding="utf-8")
        print(f"daily report written to {args.out}")
    else:
        print(content)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="weekly_report_quality", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_lint = sub.add_parser("lint", help="lint a case directory")
    p_lint.add_argument("--cases", required=True)
    p_lint.set_defaults(func=_cmd_lint)

    p_import = sub.add_parser("import", help="import markdown cases")
    p_import.add_argument("--input", required=True)
    p_import.add_argument("--out-dir", required=True)
    p_import.set_defaults(func=_cmd_import)

    def add_run_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--cases", required=True)
        p.add_argument("--evidence", required=True)
        p.add_argument("--out", required=True)
        p.add_argument("--baseline", default="")
        p.add_argument("--run-id", dest="run_id", default="")
        p.add_argument("--evaluators", default="", help="comma-separated evaluator names")
        p.add_argument("--tags", default="", help="comma-separated tag filter")
        p.add_argument("--case", default="", help="comma-separated case id filter")
        p.add_argument("--threshold", type=float, default=0.7)
        p.add_argument(
            "--resume",
            action="store_true",
            help="reuse per-case results already written under --out/<run-id>/cases",
        )

    p_run = sub.add_parser("run", help="offline evaluation run")
    add_run_args(p_run)
    p_run.add_argument("--gate", action="store_true", help="exit non-zero on fail/error")
    p_run.set_defaults(func=_cmd_run)

    p_daily = sub.add_parser("daily", help="scheduled twice-daily entrypoint")
    add_run_args(p_daily)
    p_daily.set_defaults(func=_cmd_daily)

    p_report = sub.add_parser("report", help="daily comparison report")
    p_report.add_argument("--runs-dir", required=True)
    p_report.add_argument("--date", default=dt.datetime.now().strftime("%Y%m%d"))
    p_report.add_argument("--out", default="")
    p_report.set_defaults(func=_cmd_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ContractError as exc:
        print(f"contract error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
