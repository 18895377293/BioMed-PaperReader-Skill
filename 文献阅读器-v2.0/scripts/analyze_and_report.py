#!/usr/bin/env python3
"""Analyze a paper and generate a report in one step.

Supports two modes:
  --mode pipeline  : Run the full DeepPaperNote pipeline (resolve → metadata → ... → bundle)
  --mode direct    : Extract PDF text directly via PyMuPDF and output for AI analysis (recommended)

The 'direct' mode is recommended for generating high-quality deep reading notes,
as it provides the full paper text to AI for comprehensive analysis.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

# Windows环境UTF-8编码兼容性
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

try:
    from deep_translator import GoogleTranslator, YouDaoTranslator, MyMemoryTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False


# ============================================================
# Mode 1: Direct PDF extraction (recommended)
# ============================================================

def extract_pdf_text(pdf_path: str, output_path: str | None = None) -> tuple[str, list[dict]]:
    """Extract full text from PDF using PyMuPDF and extract figure captions.

    Args:
        pdf_path: Path to the PDF file.
        output_path: Optional path to save extracted text. If None, only returns the text.

    Returns:
        Tuple of (extracted full text, list of figure captions with figure numbers)
    """
    if not FITZ_AVAILABLE:
        print("ERROR: PyMuPDF (fitz) is not installed. Install with: pip install PyMuPDF")
        sys.exit(1)

    import re

    doc = fitz.open(pdf_path)
    all_text = []
    figure_captions = []

    for i in range(doc.page_count):
        page_text = doc[i].get_text()
        all_text.append(f"=== Page {i + 1} ===\n{page_text}")

        # Extract figure captions - multiple patterns to handle different formats

        # Pattern 1: "Fig. 1 | title" or "Figure 1 - title"
        pattern1 = r"(?:Fig\.|Figure)\s*(\d+)[a-zA-Z]?\s*[\|\-\.]\s*(.+?)(?:\.|(?:\n\s*[a-z])|$)"
        matches1 = re.findall(pattern1, page_text, re.IGNORECASE | re.DOTALL)
        for match in matches1:
            fig_num = match[0]
            caption = match[1].strip()[:150]
            if caption and len(caption) > 5:
                figure_captions.append({
                    "figure_number": f"Figure{int(fig_num)}" if fig_num.isdigit() else f"Figure{fig_num}",
                    "caption": caption.replace("\n", " ").strip(),
                    "page_number": i + 1
                })

        # Pattern 2: "Fig. 1. Title" (single line with period after figure number)
        pattern2 = r"(?:Fig\.|Figure)\s*(\d+)[a-zA-Z]?\.\s+([A-Z][^\n]{10,100})"
        matches2 = re.findall(pattern2, page_text, re.IGNORECASE)
        for match in matches2:
            fig_num = match[0]
            caption = match[1].strip()
            if caption and not any(f["figure_number"] == f"Figure{fig_num}" for f in figure_captions):
                figure_captions.append({
                    "figure_number": f"Figure{int(fig_num)}" if fig_num.isdigit() else f"Figure{fig_num}",
                    "caption": caption[:150].replace("\n", " ").strip(),
                    "page_number": i + 1
                })

        # Pattern 3: "Figure X" at start of line (Nature Communications format)
        lines = page_text.split('\n')
        for j, line in enumerate(lines):
            line_stripped = line.strip()
            # Match "Figure 1:" with description on same or next line
            match = re.match(r"^(Figure \d+)[\|\-\.]\s*(.+)", line_stripped, re.IGNORECASE)
            if match:
                fig_num = match.group(1).replace("Figure ", "").strip()
                caption = match.group(2).strip()[:100]
                if caption and not any(f["figure_number"] == f"Figure{fig_num}" for f in figure_captions):
                    figure_captions.append({
                        "figure_number": f"Figure{int(fig_num)}" if fig_num.isdigit() else f"Figure{fig_num}",
                        "caption": caption.replace("\n", " ").strip(),
                        "page_number": i + 1
                    })

    full_text = "\n\n".join(all_text)

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(full_text, encoding="utf-8")
        print(f"Extracted text saved to: {out}")
        print(f"Total pages: {doc.page_count}")
        print(f"Text length: {len(full_text)} characters")
        print(f"Figure captions found: {len(figure_captions)}")

    doc.close()
    return full_text, figure_captions


def extract_pdf_images(pdf_path: str, output_dir: str) -> list[dict]:
    """Extract all images from PDF and save to output directory.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: Directory to save extracted images.

    Returns:
        List of extracted image info dicts with keys: page_number, image_index, filename, path, width, height
    """
    if not FITZ_AVAILABLE:
        print("WARNING: PyMuPDF not available, skipping image extraction")
        return []

    out_path = Path(output_dir)
    figures_dir = out_path / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    images_info: list[dict] = []
    seen_xrefs: dict[int, int] = {}
    image_count = 0

    try:
        for page_num in range(doc.page_count):
            page = doc[page_num]
            for img_index, img_info in enumerate(page.get_images(full=True), start=1):
                if not img_info:
                    continue
                xref = int(img_info[0])
                if xref in seen_xrefs:
                    continue
                seen_xrefs[xref] = seen_xrefs.get(xref, 0) + 1

                try:
                    extracted = doc.extract_image(xref)
                    image_bytes = extracted.get("image")
                    if not image_bytes:
                        continue
                    ext = extracted.get("ext", "png").lower() or "png"
                    if ext not in {"png", "jpg", "jpeg", "tiff"}:
                        ext = "png"

                    image_count += 1
                    filename = f"Figure{image_count}.{ext}"
                    output_path = figures_dir / filename

                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(image_bytes)

                    width = extracted.get("width", 0)
                    height = extracted.get("height", 0)

                    images_info.append({
                        "page_number": page_num + 1,
                        "image_index": img_index,
                        "figure_number": image_count,
                        "filename": filename,
                        "path": str(output_path),
                        "width": width,
                        "height": height,
                    })
                    print(f"  Extracted: {filename} (page {page_num + 1}, {width}x{height})")
                except Exception as e:
                    print(f"  Warning: Failed to extract image {img_index} from page {page_num + 1}: {e}")
                    continue
    finally:
        doc.close()

    print(f"Total images extracted: {len(images_info)}")
    return images_info


def generate_direct_report(pdf_path: str, output_dir: str, title_override: str = "") -> str:
    """Extract PDF text/images and generate an AI prompt template.

    Direct mode is preparation-only: it outputs extracted text, figures, and a
    structured prompt template for AI writing. It does not generate a final
    deep-reading Markdown report automatically.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: Directory to save the output files.
        title_override: Optional title override.

    Returns:
        Path to the generated prompt template file.
    """
    if not FITZ_AVAILABLE:
        print("ERROR: PyMuPDF (fitz) is not installed. Install with: pip install PyMuPDF")
        sys.exit(1)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = out_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Extract full text and figure captions
    text_path = out_dir / "extracted_text.txt"
    full_text, figure_captions = extract_pdf_text(pdf_path, str(text_path))
    print(f"Found {len(figure_captions)} figure captions")

    # Step 2: Extract images from PDF
    print("=" * 60)
    print("Extracting images from PDF...")
    print("=" * 60)
    images_info = extract_pdf_images(pdf_path, str(out_dir))

    # Step 3: Extract basic metadata from first page
    doc = fitz.open(pdf_path)
    first_page_text = doc[0].get_text() if doc.page_count > 0 else ""

    # Try to extract title from first few lines
    lines = [l.strip() for l in first_page_text.split("\n") if l.strip()]
    detected_title = ""
    for line in lines[:10]:
        if line.lower().startswith(("article", "https://", "doi:", "received:", "accepted:")):
            continue
        if len(line) > 10 and not line[0].isdigit():
            detected_title = line
            break

    title = title_override or detected_title or Path(pdf_path).stem
    page_count = doc.page_count
    doc.close()

    # Get absolute paths for images
    abs_figures_dir = figures_dir.resolve()
    abs_out_dir = out_dir.resolve()

    # Match figures with captions, sort by figure number
    figure_captions_sorted = sorted(figure_captions, key=lambda x: int(x["figure_number"].replace("Figure", "")) if x["figure_number"].replace("Figure", "").isdigit() else 0)

    # Build figure references with captions
    figures_md = ""
    figure_sections = []
    if images_info:
        matched_count = 0
        for i, img in enumerate(images_info[:12]):
            fig_num = img.get("figure_number", i + 1)
            filename = img.get("filename", "")
            abs_img_path = abs_figures_dir / filename

            # Find caption for this figure
            caption_text = ""
            for cap in figure_captions_sorted:
                cap_num = cap["figure_number"].replace("Figure", "")
                if str(fig_num) == cap_num:
                    caption_text = cap.get("caption", "")[:80]
                    break

            # Build markdown with caption
            figure_section = f"### Figure {fig_num}\n\n"
            if caption_text:
                figure_section += f"**图注**: {caption_text}\n\n"
            figure_section += f"![]({abs_img_path})\n\n"
            figure_sections.append(figure_section)
            matched_count += 1
        print(f"Embedded {matched_count} figures with captions in report")
        
        # Join all figure sections
        figures_md = "\n".join(figure_sections)

    # Step 4: Generate AI writing prompt template (not final report)
    template_content = f"""# {title}

> ★ **满满文献阅读器标准深度阅读笔记** ★

> 本报告依据**满满文献阅读器 Skill**的深度阅读笔记标准生成
> 
> **AI 指令**：请读取 `extracted_text.txt` 文件中的完整PDF内容，然后按照以下模板结构生成深度阅读笔记。
> **重要要求**：
> 1. 所有内容必须使用**中文**
> 2. 替换所有文字占位符为实际内容（如[请填写]等）
> 3. 基于PDF全文内容进行分析，不仅仅是摘要
> 4. 保持学术语言风格，提供具体数据和技术细节
> 5. **图片匹配核心规则**：
>    - 根据PDF正文内容，识别每个Figure描述的是什么（如材料制备、体外实验、体内效果、机制研究等）
>    - 在"关键结果"部分，根据正文描述的逻辑顺序，将对应的Figure图片插入到相应的位置
>    - 例如：正文先描述"Figure 2A-C显示体内治疗效果"，就把Figure 2插入到"体内治疗效果"关键结果中
>    - 不要按Figure编号顺序机械插入，要根据正文内容逻辑匹配
> 6. **图片已直接插入模板中**，在"各Figure数据结果"部分可见，**请完整保留不要删除**
> 7. 图片路径格式：`![](figures/FigureX.png)` 或绝对路径
> 
> 参考案例：`docs/案例报告_ePOWER.md`

---

## 核心信息

- **标题**: [请翻译为中文]
- **原文标题**: {title}
- **作者**: [请从文中提取]
- **年份**: [请从文中提取]
- **期刊**: [请从文中提取]
- **DOI**: [请从文中提取]
- **关键词**: [请从文中提取或总结]
- **来源**: 本地PDF
- **页数**: {page_count}

---

## 原文摘要翻译

请从extracted_text.txt的正文开始部分找到Abstract，翻译为中文：

### [请在此填写翻译后的摘要]

---

## 创新点

请基于全文内容，识别3-5个核心创新点，每点需具体说明。

### 1. [创新点1]
[具体说明，包括技术细节和效果数据]

### 2. [创新点2]
[具体说明]

### 3. [创新点3]
[具体说明]

---

## 一句话总结

请用一句话概括全文核心贡献：

### [请在此填写]

---

## 研究问题

请明确核心科学问题和研究动机。

### 核心科学问题
[请填写]

### 研究动机
[请填写，从Introduction部分提炼]

---

## 数据与任务定义

### 数据���源

请描述实验数据来源：

- **细胞模型**: [如DC2.4, RAW264.7, BMDCs等]
- **动物模型**: [如C57BL/6小鼠, B16-OVA肿瘤等]
- **样本量**: [如n=3-6/组]
- **分组设计**: [如PBS, SONA, SONA+US, SONV, SONV+US等]

### 任务定义

请列出研究验证的具体任务列表。

---

## 方法主线

请分阶段描述方法流程，使用流程图格式。

### 阶段一：[名称]
```
[方法步骤描述]
```

### 阶段二：[名称]
```
[方法步骤描述]
```

### 阶段三：[名称]
```
[方法步骤描述]
```

---

## 关键结果

请提取关键数据，用表格呈现定量结果，并按正文逻辑顺序插入对应的Figure图片。

### 定量数据表格

| 指标 | 组1 | 组2 | 组3 | 统计显著性 |
|------|-----|-----|-----|-----------|
| [指标1] | [数值] | [数值] | [数值] | |
| [指标2] | [数值] | [数值] | [数值] | |
| [指标3] | [数值] | [数值] | [数值] | |

### 关键结果1：[请根据正文填写，如"体内治疗效果"]

[请描述关键结果1的内容]

**对应图片**：`![](figures/FigureX.png)` ← 请根据正文描述替换为正确的Figure编号

### 关键结果2：[请根据正文填写，如"体外细胞实验"]

[请描述关键结果2的内容]

**对应图片**：`![](figures/FigureX.png)` ← 请根据正文描述替换为正确的Figure编号

### 关键结果3：[请根据正文填写，如"机制研究"]

[请描述关键结果3的内容]

**对应图片**：`![](figures/FigureX.png)` ← 请根据正文描述替换为正确的Figure编号

### 各Figure数据结果（参考列表）

**说明**：以下列出了所有提取的Figure及其图注。请根据正文内容，将对应的Figure图片插入到上面的关键结果描述中。

**示例匹配逻辑**：
- 正文描述"如图2A所示，体内治疗效果显著" → 在"体内治疗效果"关键结果处引用 `![](figures/Figure2.png)`
- 正文描述"图3显示体外细胞实验结果" → 在"体外实验"关键结果处引用 `![](figures/Figure3.png)`

**可用图片列表**：

{figures_md}

---

## 深度分析

请进行分析：

### 技术创新性分析
[与现有方法对比]

### 机制解析
[分子/细胞机制]

### 临床转化潜力
[应用前景]

---

## 局限性评估

请客观评估4-6项局限性。

### 1. [局限性1]
[分析]

### 2. [局限性2]
[分析]

### 3. [局限性3]
[分析]

---

## 研究启发

请总结3-5项对后续研究的启发。

### 1. [启发1]
### 2. [启发2]
### 3. [启发3]

---

## 引用

请生成标准引用格式：

**[请填写]**

---

> ★ **满满文献阅读器标准深度阅读笔记** ★
> 本报告包含：问题定义、方法说明、数据分析、创新点识别、局限性评估及研究启发
"""

    # Write template file with absolute image paths
    template_path = out_dir / "深度阅读笔记_写作提示模板.md"
    template_path.write_text(template_content, encoding="utf-8")

    print("=" * 60)
    print("满满文献阅读器 Skill - 直接提取模式（生成写作提示模板）")
    print("=" * 60)
    print(f"PDF: {pdf_path}")
    print(f"Pages: {page_count}")
    print(f"Images: {len(images_info)}")
    print(f"Full text: {text_path}")
    print(f"Prompt Template: {template_path}")
    print(f"Images dir: {figures_dir}")
    print("=" * 60)

    return str(template_path)


# ============================================================
# Mode 2: Pipeline mode (original)
# ============================================================

def run_step(step_name, cmd, workdir, step_num, total_steps):
    """Run a step and return the output."""
    print(f"[{step_num}/{total_steps}] Running {step_name}...")
    print(f"Command: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=str(workdir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    if result.returncode != 0:
        print(f"Error running {step_name}:")
        print(f"Stderr: {result.stderr}")
        print(f"Stdout: {result.stdout}")
        raise SystemExit(f"{step_name} failed with exit code {result.returncode}")
    print(f"[{step_num}/{total_steps}] {step_name} completed successfully!")
    return result.stdout


def translate_english_to_chinese(text: str) -> str:
    """Translate English to Chinese"""
    if not text:
        return ""

    text = text.strip()

    if not TRANSLATOR_AVAILABLE:
        return text

    if len(text) > 5000:
        text = text[:5000]

    translators = [
        lambda t: MyMemoryTranslator(source='en', target='zh-CN').translate(t),
        lambda t: YouDaoTranslator(source='en', target='zh-CN').translate(t),
        lambda t: GoogleTranslator(source='en', target='zh-CN').translate(t),
    ]

    for i, translator_func in enumerate(translators):
        try:
            translated = translator_func(text)
            if translated and translated != text:
                return translated
        except Exception as e:
            print(f"Translator {i+1} failed: {e}")
            continue

    return text


def extract_abstract_from_text(full_text: str) -> tuple[str, str]:
    """Extract abstract and title from PDF full text.

    Returns:
        tuple: (abstract_text, title_candidate)
    """
    if not full_text:
        return "", ""
    
    import re
    
    lines = full_text.split("\n")
    
    title_candidate = ""
    abstract_start = -1
    abstract_end = -1
    
    for i, line in enumerate(lines[:30]):
        line_clean = line.strip()
        if not line_clean:
            continue
        
        line_lower = line_clean.lower()
        
        if i < 15 and len(line_clean) > 15:
            if title_candidate == "" and not any(token in line_lower for token in ["abstract", "article", "https://", "doi:", "received:", "accepted:", "copyright", "journal"]):
                if not line_clean[0].isdigit() and not line_clean.startswith("Figure"):
                    title_candidate = line_clean
        
        if "abstract" in line_lower and len(line_clean) < 200:
            abstract_start = i + 1
            continue
        
        if abstract_start > 0 and abstract_end < 0:
            if re.match(r"^(introduction|keywords?|1\.|background|method|results?|discussion|conclusion)", line_lower):
                abstract_end = i
                break
    
    abstract_text = ""
    if abstract_start > 0:
        if abstract_end > abstract_start:
            abstract_lines = lines[abstract_start:abstract_end]
        else:
            abstract_lines = lines[abstract_start:abstract_start + 30]
        abstract_text = " ".join(line.strip() for line in abstract_lines if line.strip())
        abstract_text = re.sub(r"\s+", " ", abstract_text).strip()
    
    return abstract_text, title_candidate


def extract_author_and_metadata(first_page_text: str) -> dict:
    """Extract author, journal, DOI from first page"""
    import re
    metadata = {
        "authors": [],
        "year": "",
        "journal": "",
        "doi": ""
    }
    
    if not first_page_text:
        return metadata
    
    year_match = re.search(r"\b(19|20)\d{2}\b", first_page_text)
    if year_match:
        metadata["year"] = year_match.group()
    
    doi_match = re.search(r"doi[:\s]+(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", first_page_text, re.IGNORECASE)
    if doi_match:
        metadata["doi"] = doi_match.group(1).rstrip(").,;")
    
    lines = first_page_text.split("\n")
    for line in lines[:20]:
        if "@" in line or "edu" in line.lower() or "university" in line.lower() or "hospital" in line.lower():
            continue
        if len(line.strip()) > 3 and len(line.strip()) < 100:
            if not line.strip()[0].isdigit() and "figure" not in line.lower():
                if "author" not in line.lower() and "journal" not in line.lower():
                    potential_author = line.strip().rstrip(",;")
                    if len(potential_author) > 3 and len(potential_author.split()) <= 5:
                        if potential_author not in metadata["authors"]:
                            metadata["authors"].append(potential_author)
    
    journal_patterns = [
        r"journal[:\s]+([^\n]+)",
        r"[A-Z][a-z]+[\s][A-Za-z]+[:\s]+[A-Z]",
    ]
    for pattern in journal_patterns:
        match = re.search(pattern, first_page_text, re.IGNORECASE)
        if match:
            metadata["journal"] = match.group(1).strip()
            break
    
    return metadata


def extract_key_info(bundle_data: dict) -> dict:
    """Extract key info from bundle data"""
    info = {
        "title": bundle_data.get("title", ""),
        "authors": [],
        "affiliations": [],
        "year": "",
        "abstract_cn": "",
        "keywords": [],
        "translated_title": "",
        "doi": "",
        "journal": "",
    }

    metadata = bundle_data.get("metadata", {})
    if isinstance(metadata, dict):
        info["title"] = metadata.get("title", info["title"])
        info["translated_title"] = metadata.get("translated_title", "")
        info["authors"] = metadata.get("authors", [])
        info["affiliations"] = metadata.get("affiliations", [])
        info["year"] = metadata.get("year", "")
        info["doi"] = metadata.get("doi", "")
        info["journal"] = metadata.get("journal", "")

    evidence = bundle_data.get("evidence", {})
    if isinstance(evidence, dict):
        if "abstract" in evidence:
            abstract_text = evidence["abstract"]
            if isinstance(abstract_text, list) and len(abstract_text) > 0:
                raw_text = abstract_text[0].get("text", "")
                info["abstract_cn"] = translate_english_to_chinese(raw_text)
            elif isinstance(abstract_text, str):
                info["abstract_cn"] = translate_english_to_chinese(abstract_text)

    return info


def generate_markdown_from_bundle(bundle_path: Path) -> str:
    """Generate Markdown note from synthesis bundle"""
    bundle_content = bundle_path.read_text(encoding="utf-8")
    bundle_data = json.loads(bundle_content)

    title = bundle_data.get("title", "")
    candidate_chunks = bundle_data.get("candidate_chunks", {})
    figure_plan = bundle_data.get("figure_plan", {})

    key_info = extract_key_info(bundle_data)

    # Classify chunks by category
    results_texts = []
    method_texts = []
    task_texts = []
    innovation_texts = []
    limitation_texts = []
    discussion_texts = []

    for category, texts in candidate_chunks.items():
        if isinstance(texts, list):
            for item in texts:
                if isinstance(item, dict) and "text" in item:
                    text = item["text"]
                    if category in ["experiment", "results"]:
                        results_texts.append(text)
                    elif category == "method":
                        method_texts.append(text)
                    elif category == "task":
                        task_texts.append(text)
                    elif category == "innovation":
                        innovation_texts.append(text)
                    elif category == "limitation":
                        limitation_texts.append(text)
                    elif category in ["discussion", "conclusion"]:
                        discussion_texts.append(text)

    # Translate top chunks (limit to avoid API overload)
    translated_abstract = key_info["abstract_cn"] or "未提取到摘要信息"
    translated_results = translate_english_to_chinese(" ".join(results_texts[:3])) if results_texts else ""
    translated_method = translate_english_to_chinese(" ".join(method_texts[:3])) if method_texts else ""
    translated_task = translate_english_to_chinese(" ".join(task_texts[:3])) if task_texts else ""
    translated_innovations = translate_english_to_chinese(" ".join(innovation_texts[:3])) if innovation_texts else ""
    translated_limitations = translate_english_to_chinese(" ".join(limitation_texts[:3])) if limitation_texts else ""
    translated_discussion = translate_english_to_chinese(" ".join(discussion_texts[:3])) if discussion_texts else ""

    # Build figure placeholders
    figures_md = ""
    if figure_plan and isinstance(figure_plan, dict):
        figures = figure_plan.get("figures", [])
        if isinstance(figures, list):
            for fig in figures[:8]:
                if isinstance(fig, dict):
                    fig_id = fig.get("id", "Fig. ?")
                    caption = fig.get("caption", "")
                    location = fig.get("suggested_location", "")
                    figures_md += f"> [!figure] {fig_id} {caption}\n> 建议位置：{location}\n\n"

    # Build metadata section
    author_str = ", ".join(key_info["authors"]) if key_info["authors"] else "未知作者"
    year_str = key_info["year"] or "未知年份"
    keywords = key_info.get("keywords", [])
    keywords_str = "、".join(keywords) if keywords else "未提取到关键词"
    doi_str = key_info.get("doi", "")
    journal_str = key_info.get("journal", "")
    translated_title = key_info.get("translated_title", "")

    # Build core info lines
    core_info_lines = [
        f"- 标题: {translated_title or title}",
        f"- 原文标题: {title}" if translated_title else "",
        f"- 作者: {author_str}",
        f"- 年份: {year_str}",
    ]
    if journal_str:
        core_info_lines.append(f"- 期刊: {journal_str}")
    if doi_str:
        core_info_lines.append(f"- DOI: {doi_str}")
    core_info_lines.extend([
        f"- 关键词: {keywords_str}",
        f"- 来源: 本地PDF",
    ])
    core_info = "\n".join(line for line in core_info_lines if line)

    # Build citation
    citation_parts = [author_str]
    citation_parts.append(f"{title}")
    if journal_str:
        citation_parts.append(f"*{journal_str}*")
    citation_parts.append(f"({year_str})")
    if doi_str:
        citation_parts.append(f"https://doi.org/{doi_str}")
    citation = ". ".join(citation_parts)

    # Assemble report
    markdown = f"""# {title}

## 核心信息

{core_info}

## 原文摘要翻译

{translated_abstract}

## 创新点

{translated_innovations or "> 未提取到创新点信息，请基于全文内容手动补充"}

## 一句话总结

{translated_task or "> 未提取到任务信息，请基于全文内容手动补充"}

## 研究问题

{translated_task or "> 未提取到研究问题信息，请基于全文内容手动补充"}

## 数据与任务定义

### 数据来源

{translated_results or "> 未提取到数据来源信息，请基于全文内容手动补充"}

### 任务定义

{translated_task or "> 未提取到任务定义信息，请基于全文内容手动补充"}

## 方法主线

{translated_method or "> 未提取到方法信息，请基于全文内容手动补充"}

## 关键结果

{figures_md if figures_md else "> [图 — 未提取到图表信息]"}

{translated_results or "> 未提取到结果信息，请基于全文内容手动补充"}

## 深度分析

{translated_discussion or translated_results or "> 未提取到深度分析信息，请基于全文内容手动补充"}

## 局限性评估

{translated_limitations or "> 未提取到局限性信息，请基于全文内容手动补充"}

## 研究启发

> 请基于全文内容和对领域的理解，补充研究启发

## 引用

- {citation}

---

> 本报告依据满满文献阅读器 Skill 的深度阅读笔记标准生成，包含：问题定义、方法说明、数据分析、创新点识别、局限性评估及研究启发。
"""

    return markdown


def copy_images_to_output(assets_path: Path, target_images_dir: Path) -> int:
    """Copy images to target directory"""
    if not assets_path.exists():
        return 0

    assets_data = json.loads(assets_path.read_text(encoding="utf-8"))
    asset_root = Path(assets_data.get("asset_root", ""))
    if not asset_root.exists():
        return 0

    image_count = 0
    image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".tiff"}

    for img_path in asset_root.rglob("*"):
        if img_path.is_file():
            suffix = Path(img_path).suffix.lower()
            if suffix in image_extensions:
                try:
                    target_img_path = target_images_dir / img_path.name
                    shutil.copy2(str(img_path), str(target_img_path))
                    image_count += 1
                except Exception:
                    pass

    return image_count


def run_pipeline_mode(args) -> None:
    """Run the full pipeline mode (original behavior)."""
    scripts_dir = Path(__file__).resolve().parent
    workdir = Path(args.workdir).expanduser().resolve()
    workdir.mkdir(parents=True, exist_ok=True)

    py = sys.executable
    total_steps = 10

    print("=" * 60)
    print("满满文献阅读器 Skill - 文献分析（Pipeline 模式）")
    print("=" * 60)
    print(f"Input: {args.input}")
    print(f"Output Directory: {'Obsidian Vault' if not args.output_dir else args.output_dir}")
    print(f"Workdir: {workdir}")
    print(f"Prefix: {args.prefix}")
    if TRANSLATOR_AVAILABLE:
        print("Translation: MyMemory/YouDao/Google (EN -> ZH-CN)")
    else:
        print("Translation: Not available (using raw text)")
    print("=" * 60)

    resolve_cmd = [
        py,
        str(scripts_dir / "resolve_paper.py"),
        "--input", args.input,
        "--output", f"{args.prefix}_resolve.json"
    ]
    run_step("Resolve Paper", resolve_cmd, workdir, 1, total_steps)

    metadata_cmd = [
        py,
        str(scripts_dir / "collect_metadata.py"),
        "--input", args.input,
        "--output", f"{args.prefix}_metadata.json"
    ]
    run_step("Collect Metadata", metadata_cmd, workdir, 2, total_steps)

    fetch_cmd = [
        py,
        str(scripts_dir / "fetch_pdf.py"),
        "--input", args.input,
        "--output", f"{args.prefix}_fetch.json"
    ]
    run_step("Fetch PDF", fetch_cmd, workdir, 3, total_steps)

    evidence_cmd = [
        py,
        str(scripts_dir / "extract_evidence.py"),
        "--input", f"{args.prefix}_fetch.json",
        "--output", f"{args.prefix}_evidence.json"
    ]
    run_step("Extract Evidence", evidence_cmd, workdir, 4, total_steps)

    assets_cmd = [
        py,
        str(scripts_dir / "extract_pdf_assets.py"),
        "--input", f"{args.prefix}_fetch.json",
        "--output", f"{args.prefix}_assets.json"
    ]
    run_step("Extract PDF Assets", assets_cmd, workdir, 5, total_steps)

    figures_cmd = [
        py,
        str(scripts_dir / "plan_figures.py"),
        "--evidence", f"{args.prefix}_evidence.json",
        "--assets", f"{args.prefix}_assets.json",
        "--output", f"{args.prefix}_figures.json"
    ]
    run_step("Plan Figures", figures_cmd, workdir, 6, total_steps)

    bundle_cmd = [
        py,
        str(scripts_dir / "build_synthesis_bundle.py"),
        "--metadata", f"{args.prefix}_metadata.json",
        "--evidence", f"{args.prefix}_evidence.json",
        "--figures", f"{args.prefix}_figures.json",
        "--assets", f"{args.prefix}_assets.json",
        "--output", f"{args.prefix}_bundle.json"
    ]
    run_step("Build Synthesis Bundle", bundle_cmd, workdir, 7, total_steps)

    print("[8/10] Generating Markdown Report...")
    bundle_path = workdir / f"{args.prefix}_bundle.json"
    markdown_content = generate_markdown_from_bundle(bundle_path)
    markdown_path = workdir / f"{args.prefix}_note.md"
    markdown_path.write_text(markdown_content, encoding="utf-8")
    print("[8/10] Generate Markdown Report completed successfully!")

    report_cmd = [
        py,
        str(scripts_dir / "write_obsidian_note.py"),
        "--input", f"{args.prefix}_metadata.json",
        "--content-file", str(markdown_path),
        "--title", args.title or ""
    ]
    if args.output_dir:
        report_cmd.extend(["--subdir", args.output_dir])

    report_output = run_step("Write to Obsidian", report_cmd, workdir, 9, total_steps)

    print("[10/10] Copying Images to Output Directory...")
    try:
        output_json = json.loads(report_output)
        if "note_path" in output_json:
            note_path = Path(output_json["note_path"])
            target_images_dir = note_path.parent / "images"
            target_images_dir.mkdir(parents=True, exist_ok=True)

            assets_path = workdir / f"{args.prefix}_assets.json"
            image_count = copy_images_to_output(assets_path, target_images_dir)
            if image_count > 0:
                print(f"[10/10] Copy Images completed successfully! Copied {image_count} images.")
            else:
                print("  No images found to copy.")
        else:
            print("  Could not determine output directories.")
    except Exception as e:
        print(f"  Error copying images: {e}")

    print("=" * 60)
    print("满满文献阅读器 Skill - 分析完成!")
    print("=" * 60)
    print("Report has been generated and saved to:")

    try:
        output_json = json.loads(report_output)
        if "note_path" in output_json:
            print(f"  - {output_json['note_path']}")
            print(f"  - Images: {output_json.get('images_dir', '')}")
        else:
            print("  - Obsidian Vault")
    except Exception as e:
        print(f"  - Obsidian Vault (Error parsing output: {e})")

    print("=" * 60)


# ============================================================
# Main entry point
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__ or "analyze and report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Recommended: Direct mode (extract PDF text for AI analysis)
  python analyze_and_report.py --mode direct --input "paper.pdf" --output-dir "output"

  # Pipeline mode (run full DeepPaperNote pipeline)
  python analyze_and_report.py --mode pipeline --input "paper.pdf" --output-dir "output"
"""
    )
    parser.add_argument("--input", required=True, help="PDF file path or paper reference")
    parser.add_argument("--mode", choices=["direct", "pipeline"], default="direct",
                        help="Analysis mode: 'direct' (recommended, extract PDF for AI) "
                             "or 'pipeline' (run full DeepPaperNote pipeline)")
    parser.add_argument("--output-dir", default="", help="Output directory for reports")
    parser.add_argument("--title", default="", help="Explicit title override")
    parser.add_argument("--prefix", default="run", help="Prefix for intermediate files (pipeline mode only)")
    parser.add_argument("--workdir", default="tmp/LiteratureReader_runs",
                        help="Working directory for intermediate files (pipeline mode only)")
    args = parser.parse_args()

    if args.mode == "direct":
        if not args.output_dir:
            # Default output directory based on PDF filename
            pdf_stem = Path(args.input).stem
            args.output_dir = str(Path(args.input).parent / f"文献分析_{pdf_stem}")
        generate_direct_report(args.input, args.output_dir, args.title)
    else:
        run_pipeline_mode(args)


if __name__ == "__main__":
    main()
