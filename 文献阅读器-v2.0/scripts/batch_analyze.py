#!/usr/bin/env python3
"""Batch analyze multiple papers in a folder and generate reports."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Windows环境UTF-8编码兼容性
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def get_pdf_files(folder_path: str) -> list[Path]:
    """Get all PDF files from the given folder."""
    folder = Path(folder_path).expanduser().resolve()
    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder}")
    if not folder.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {folder}")

    pdf_files = []
    for ext in ["*.pdf", "*.PDF"]:
        pdf_files.extend(folder.glob(ext))
        for subfolder in folder.rglob("*"):
            if subfolder.is_dir():
                pdf_files.extend(subfolder.glob(ext))

    return sorted(list(set(pdf_files)))

def analyze_single_paper(
    pdf_path: Path,
    output_dir: str,
    template: str,
    max_workers: int,
    workdir: Path
) -> dict:
    """Analyze a single paper and return the result."""
    try:
        scripts_dir = Path(__file__).resolve().parent
        py = sys.executable

        prefix = f"paper_{pdf_path.stem[:20]}"
        run_dir = workdir / f"runs_{pdf_path.stem[:20]}"
        run_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            py,
            str(scripts_dir / "analyze_and_report.py"),
            "--input", str(pdf_path),
            "--output-dir", output_dir,
            "--template", template,
            "--prefix", prefix,
            "--workdir", str(run_dir)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        return {
            "status": "success" if result.returncode == 0 else "failed",
            "paper": str(pdf_path),
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        return {
            "status": "error",
            "paper": str(pdf_path),
            "error": str(e)
        }

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__ or "batch analyze papers and generate reports")
    parser.add_argument("--input", required=True, help="Folder path containing PDF files")
    parser.add_argument("--output-dir", default="", help="Output directory for reports")
    parser.add_argument("--template", default="academic", help="Note template to use (default, academic, technical, summary)")
    parser.add_argument("--max-workers", type=int, default=3, help="Maximum number of parallel workers")
    parser.add_argument("--workdir", default="tmp/batch_analysis", help="Working directory for intermediate files")
    parser.add_argument("--report", default="batch_analysis_report.json", help="Output path for batch analysis report")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    workdir = Path(args.workdir).expanduser().resolve()
    workdir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("满满文献阅读器 Skill - 批量分析")
    print("=" * 60)
    print(f"Input Folder: {input_path}")
    print(f"Output Directory: {args.output_dir or 'Obsidian Vault'}")
    print(f"Template: {args.template}")
    print(f"Max Workers: {args.max_workers}")
    print(f"Workdir: {workdir}")
    print("=" * 60)

    pdf_files = get_pdf_files(str(input_path))
    total_papers = len(pdf_files)

    if total_papers == 0:
        print("No PDF files found in the specified folder.")
        return

    print(f"Found {total_papers} PDF files to analyze.")
    print("-" * 60)

    results = []
    start_time = datetime.now()

    if args.max_workers == 1:
        for idx, pdf_path in enumerate(pdf_files, 1):
            print(f"[{idx}/{total_papers}] Analyzing: {pdf_path.name}")
            result = analyze_single_paper(
                pdf_path,
                args.output_dir,
                args.template,
                args.max_workers,
                workdir
            )
            results.append(result)
            status = "OK" if result["status"] == "success" else "FAIL"
            print(f"[{idx}/{total_papers}] {status}: {pdf_path.name}")
            print()
    else:
        with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            future_to_pdf = {
                executor.submit(
                    analyze_single_paper,
                    pdf_path,
                    args.output_dir,
                    args.template,
                    args.max_workers,
                    workdir
                ): pdf_path
                for pdf_path in pdf_files
            }

            completed = 0
            for future in as_completed(future_to_pdf):
                completed += 1
                pdf_path = future_to_pdf[future]
                result = future.result()
                results.append(result)
                status = "OK" if result["status"] == "success" else "FAIL"
                print(f"[{completed}/{total_papers}] {status}: {pdf_path.name}")

    end_time = datetime.now()
    duration = end_time - start_time

    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] == "failed")
    error_count = sum(1 for r in results if r["status"] == "error")

    print()
    print("=" * 60)
    print("Batch Analysis Completed")
    print("=" * 60)
    print(f"Total Papers: {total_papers}")
    print(f"Successful: {success_count}")
    print(f"Failed: {failed_count}")
    print(f"Errors: {error_count}")
    print(f"Duration: {duration}")
    print("=" * 60)

    report = {
        "timestamp": start_time.isoformat(),
        "input_folder": str(input_path),
        "output_directory": args.output_dir or "Obsidian Vault",
        "template": args.template,
        "total_papers": total_papers,
        "successful": success_count,
        "failed": failed_count,
        "errors": error_count,
        "duration_seconds": duration.total_seconds(),
        "results": results
    }

    report_path = workdir / args.report
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"Batch report saved to: {report_path}")
    print("=" * 60)

    if args.output_dir:
        print(f"All reports have been saved to: {args.output_dir}")
    else:
        print("All reports have been saved to the Obsidian Vault")

    print()
    print("Failed Papers:")
    for r in results:
        if r["status"] != "success":
            print(f"  - {r['paper']}")
            if r["status"] == "failed" and "stderr" in r:
                print(f"    Error: {r['stderr'][:200]}")

if __name__ == "__main__":
    main()
