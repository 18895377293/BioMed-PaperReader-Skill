#!/usr/bin/env python3
"""Write the final Markdown note into an Obsidian-style vault."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.common import (
    emit,
    ensure_parent,
    maybe_load_json_record,
    resolve_domain_subdir,
    resolve_note_output_mode,
    resolve_obsidian_note_path,
    runtime_config,
)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__ or "write obsidian note")
    p.add_argument("--input", default="", help="Metadata JSON path or JSON string.")
    p.add_argument("--content-file", default="", help="Path to the final Markdown content.")
    p.add_argument("--content", default="", help="Inline Markdown content.")
    p.add_argument("--stdin", action="store_true", help="Read Markdown content from stdin.")
    p.add_argument("--lint-json", default="", help="Optional lint JSON path. Refuse write if structure, style, or math gate failed.")
    p.add_argument("--title", default="", help="Explicit title override.")
    p.add_argument("--output", default="", help="JSON status output path.")
    p.add_argument("--vault", default="", help="Target Obsidian vault path.")
    p.add_argument("--subdir", default="", help="Vault-relative subdirectory.")
    p.add_argument("--filename", default="", help="Explicit note filename.")
    p.add_argument("--asset-subdir", default="images", help="Asset folder name relative to the note directory.")
    p.add_argument("--paper-id", default="", help="Canonical paper id.")
    p.add_argument("--template", default="default", help="Note template to use (default, academic, technical, summary).")
    return p


def apply_note_template(note_text: str, template: str, record: dict[str, Any]) -> str:
    """Apply the specified template to the note content."""
    if template == "default":
        return note_text
    
    # 提取元数据
    title = str(record.get("title", "")).strip()
    authors = record.get("authors", [])
    author_names = []
    for author in authors:
        if isinstance(author, dict):
            author_names.append(author.get("name", ""))
        else:
            author_names.append(str(author))
    authors_str = ", ".join(author_names) if author_names else ""
    year = str(record.get("year", "")).strip()
    doi = str(record.get("doi", "")).strip()
    abstract = str(record.get("abstract", "")).strip()
    venue = str(record.get("venue", "")).strip()
    
    # 定义不同的模板
    if template == "academic":
        # 学术风格模板
        template_content = f"""# {title}

## 基本信息
- **作者**: {authors_str}
- **年份**: {year}
- **期刊/会议**: {venue}
- **DOI**: {doi}

## 摘要
{abstract}

## 内容
{note_text}

## 引用
```bibtex
@article{{{record.get("paper_id", "").replace(":", "_").lower()},
    title = "{title}",
    authors = "{authors_str}",
    year = "{year}",
    journal = "{venue}",
    doi = "{doi}"
}}
```
"""
    elif template == "technical":
        # 技术风格模板
        # 技术风格模板
        if doi:
            reference_link = f"- [论文链接](https://doi.org/{doi}) ({doi})"
        else:
            reference_link = f"- [论文链接](https://doi.org/{doi})"
        
        template_content = f"""# {title}

## 技术概览
- **作者**: {authors_str}
- **发布年份**: {year}
- **来源**: {venue}
- **DOI**: {doi}

## 研究背景
{abstract}

## 技术内容
{note_text}

## 关键技术点

## 应用场景

## 代码实现

## 参考链接
{reference_link}
"""
    elif template == "summary":
        # 摘要风格模板
        template_content = f"""# {title}

### 基本信息
- **作者**: {authors_str}
- **年份**: {year}
- **来源**: {venue}

### 核心问题

### 创新点

### 研究方法

### 主要结果

### 结论

### 详细内容
{note_text}
"""
    else:
        # 默认模板
        return note_text
    
    return template_content


def main() -> None:
    args = parser().parse_args()

    record = maybe_load_json_record(args.input) or {}
    title = args.title or str(record.get("title", "")).strip()
    if not title:
        raise SystemExit("write_obsidian_note.py requires --title or metadata with a title.")

    if args.lint_json:
        lint = json.loads(Path(args.lint_json).expanduser().resolve().read_text(encoding="utf-8"))
        if not lint.get("passes_basic_structure", False):
            raise SystemExit("write_obsidian_note.py refused to write note because basic structure lint failed.")
        if not lint.get("passes_style_gate", False):
            raise SystemExit("write_obsidian_note.py refused to write note because style gate failed.")
        if not lint.get("passes_math_gate", False):
            raise SystemExit("write_obsidian_note.py refused to write note because math gate failed.")

    if args.content_file:
        note_text = Path(args.content_file).expanduser().resolve().read_text(encoding="utf-8")
    elif args.content:
        note_text = args.content
    elif args.stdin:
        note_text = sys.stdin.read()
    else:
        raise SystemExit("write_obsidian_note.py requires --content-file, --content, or --stdin.")

    # 应用模板
    note_text = apply_note_template(note_text, args.template, record)

    config = runtime_config()
    if args.vault:
        config["obsidian_vault"] = args.vault
    resolved_subdir = resolve_domain_subdir(
        config,
        title=title,
        abstract=str(record.get("abstract", "")),
        subdir=args.subdir,
    )

    target_path = resolve_obsidian_note_path(
        config,
        title=title,
        subdir=resolved_subdir,
        filename=args.filename,
    )
    ensure_parent(target_path)
    Path(target_path).write_text(note_text, encoding="utf-8")
    asset_dir = target_path.parent / args.asset_subdir
    asset_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "status": "ok",
        "script": "write_obsidian_note.py",
        "paper_id": args.paper_id or record.get("paper_id", ""),
        "title": title,
        "note_path": str(target_path),
        "subdir": resolved_subdir,
        "images_dir": str(asset_dir),
        "template": args.template,
    }
    output_mode, root_path = resolve_note_output_mode(config)
    payload["output_mode"] = output_mode
    payload["base_output_root"] = str(root_path)
    if config.get("obsidian_vault"):
        payload["vault"] = str(Path(config["obsidian_vault"]).expanduser().resolve())
    emit(payload, args.output)


if __name__ == "__main__":
    main()
