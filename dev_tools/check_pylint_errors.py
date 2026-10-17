# -*- coding: utf-8 -*-
"""Local pylint error-level pre-check for shipped behavior-pack Python.

Usage: check_pylint_errors.py [behavior-pack-dir] [--out report.txt]
Exit 0: no findings; 1: findings; 2: no targets or unavailable environment.
This auxiliary check does not guarantee an identical platform toolchain.
"""

from __future__ import print_function

import argparse
import os
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
MCSTUDIO = WORKSPACE / "mcstudio_project"


def _resolve_pylint_python():
    """优先环境变量 PYLINT_PYTHON，其次工作区 venv，最后当前解释器。"""
    candidates = [
        os.environ.get("PYLINT_PYTHON"),
        os.environ.get("NETEASE_TOOLS_PYTHON"),
        str(WORKSPACE / "dev_tools" / "python_env" / "Scripts" / "python.exe"),
        str(WORKSPACE / "dev_tools" / "python_env" / "bin" / "python"),
        sys.executable,
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    return Path(sys.executable)


PYLINT_PY = _resolve_pylint_python()
TEMPLATE = "{path}:{line}:{column}: {symbol} {msg}"


def default_targets():
    """mcstudio_project 下每个工程的所有行为包。"""
    return sorted(path for path in MCSTUDIO.glob("*/behavior_packs/*")
                  if path.is_dir())


def scan(target):
    """对一个目录跑 error 级 pylint，返回（扫过的文件数, 命中行列表）。"""
    files = sorted(str(path) for path in target.rglob("*.py"))
    if not files:
        return 0, []
    cmd = [str(PYLINT_PY), "-m", "pylint", "--disable=all", "--enable=E",
           "--disable=E0401", "--score=no", "--persistent=n",
           "--msg-template=%s" % TEMPLATE] + files
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    findings = [line for line in stdout.splitlines()
                if line.strip() and ":" in line and "Module " not in line]
    if stderr.strip():
        findings += ["# stderr: %s" % line for line in stderr.splitlines()
                     if line.strip()]
    if result.returncode and not findings:
        findings.append("# pylint exited with code %s without diagnostics" % result.returncode)
    return len(files), findings


def main():
    parser = argparse.ArgumentParser(description="pylint error-level pre-check")
    parser.add_argument("target", nargs="?",
                        help="行为包目录；省略则扫描 mcstudio_project 下全部行为包")
    parser.add_argument("--out", help="把报告写到这个文件（utf-8）")
    parser.add_argument("--exclude-project", action="append", default=[],
                        help="跳过指定工程目录名；可重复指定，用于排除正在开发的工程")
    args = parser.parse_args()

    if not PYLINT_PY.exists():
        print("pylint interpreter not found: %s" % PYLINT_PY)
        return 2
    if not MCSTUDIO.is_dir():
        print("mcstudio_project not found: %s" % MCSTUDIO)
        return 2

    if args.target:
        targets = [Path(args.target).resolve()]
        if not targets[0].is_dir():
            print("not a directory: %s" % targets[0])
            return 2
    else:
        targets = default_targets()
        if not targets:
            print("no behavior pack found under %s" % MCSTUDIO)
            return 2

    targets = [p for p in targets if p.parent.parent.name not in args.exclude_project]
    if not targets:
        print("no targets remain after exclusions")
        return 2
    probe = subprocess.run([str(PYLINT_PY), "-m", "pylint", "--version"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    if probe.returncode:
        print("pylint unavailable in the selected interpreter; install tool dependencies")
        return 2
    report = [u"# pylint error-level pre-check (platform machine review code 18)",
              u"# version = %s" % probe.stdout.splitlines()[0],
              u"# pylint = %s" % PYLINT_PY,
              u"# targets = %d" % len(targets),
              u""]
    def display_target(path):
        try:
            return path.relative_to(WORKSPACE)
        except ValueError:
            return path

    total_findings = 0
    for target in targets:
        scanned, findings = scan(target)
        total_findings += len(findings)
        print("%s: scanned=%d findings=%d"
              % (display_target(target), scanned, len(findings)))
        report.append(u"## %s (scanned=%d findings=%d)"
                      % (display_target(target), scanned,
                         len(findings)))
        report += findings
        report.append(u"")
    report.append(u"# TOTAL_FINDINGS=%d" % total_findings)
    print("TOTAL_FINDINGS=%d" % total_findings)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(u"\n".join(report) + u"\n", encoding="utf-8")
        print("report written to %s" % out)
    return 1 if total_findings else 0


if __name__ == "__main__":
    sys.exit(main())
