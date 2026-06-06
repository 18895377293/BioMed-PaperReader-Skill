#!/usr/bin/env python3
# ★ 满满文献阅读器 - 深度阅读报告生成器 ★
# Minimal, robust deep-reading report generator for local PDFs
import sys
import os
import re
from pathlib import Path

print("=" * 60)
print("★ 满满文献阅读器 Skill - 深度阅读报告生成器 ★")
print("=" * 60)

# Windows环境UTF-8编码兼容性
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    import fitz  # PyMuPDF
    FITZ = True
except Exception:
    FITZ = False


def extract_pdf_text(pdf_path: str) -> str:
    if not FITZ:
        print("PyMuPDF is not installed. Please install with: pip install PyMuPDF")
        return ""
    try:
        doc = fitz.open(pdf_path)
        parts = []
        for i in range(doc.page_count):
            parts.append(doc[i].get_text("text"))
        return "\n".join(parts)
    except Exception as e:
        print(f"Failed to extract text from PDF: {e}")
        return ""


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower())


def generate_report(pdf_path: str, output_dir: str) -> Path:
    text = extract_pdf_text(pdf_path)
    title = None
    first_line = text.splitlines()[0] if text else "Unknown Title"
    title = first_line.strip() if first_line.strip() else "Unknown Title"
    slug = slugify(title)[:80]
    out_path = Path(output_dir) / f"深度阅读笔记_初稿_{slug}.md"

    # Simple, robust sections extraction using heuristics
    sections = {
        "核心信息": [],
        "研究问题": [],
        "数据与方法": [],
        "关键结果": [],
        "深度分析": [],
        "局限": [],
        "我的笔记": []
    }

    def append_section(key, line):
        if len(line.strip()):
            sections[key].append(line.strip())

    # Try to extract abstract-like content
    abstract_patterns = [r"摘要[:：]\s*(.*?)((?:\n|$){1,4})", r"Abstract[:：]?\s*(.*?)((?:\n|$){1,4})"]
    for pat in abstract_patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            for para in re.split(r"\n{2,}", m.group(1).strip()):
                if para:
                    append_section("核心信息", para)
            break

    # Very naive extraction for other sections via keywords
    for line in text.splitlines():
        l = line.strip()
        if not l:
            continue
        if re.search(r"创新|contribution|contributions|novelty|novel|关键点", l, re.IGNORECASE):
            append_section("深度分析", l)
        if re.search(r"方法|Materials|Methods|实验|实验部分|数据", l, re.IGNORECASE):
            append_section("数据与方法", l)
        if re.search(r"结果|results|结论|conclusion|effect|效果", l, re.IGNORECASE):
            append_section("关键结果", l)
        if re.search(r"局限|limitation|limitations|限制", l, re.IGNORECASE):
            append_section("局限", l)
        if re.search(r"研究问题|research question|problem|question", l, re.IGNORECASE):
            append_section("研究问题", l)
        if re.search(r"笔记|note|我的笔记", l, re.IGNORECASE):
            append_section("我的笔记", l)

    # Fallback: if sections empty, create a generic summary
    if not any(sections[k] for k in sections):
        sections["深度分析"].append("未能自动提取详细章节，以下为简要分析：该文献探讨了...（请基于全文内容完善）")

    md_lines = [
        f"# {title}",
        "",
        "> ★ **满满文献阅读器标准深度阅读笔记** ★",
        "",
        f"> 本报告依据**满满文献阅读器 Skill**的深度阅读笔记标准生成",
        "",
        "---",
        ""
    ]
    for sec, items in sections.items():
        md_lines.append(f"## {sec}")
        if items:
            for it in items:
                md_lines.append(f"- {it}")
        else:
            md_lines.append("- 未提取到该部分内容")
        md_lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"报告已生成：{out_path}")
    return out_path


def main():
    if len(sys.argv) < 3:
        print("Usage: simple_deep_report.py <input.pdf> <output-dir>")
        sys.exit(1)
    pdf = sys.argv[1]
    outdir = sys.argv[2]
    generate_report(pdf, outdir)


if __name__ == "__main__":
    main()
