# 满满文献阅读器 Skill

> 创作者：满满
> 版本：v2.0 — 教授级深度分析版

基于 Python 脚本体系的文献深度分析工具，将一篇研究论文解析为结构化深度阅读笔记。支持 PDF 全文提取、批判性分析、跨文献定量基准对比、教授级综合评判。

## 目录结构

```
文献阅读器/
├── core/              # 核心文件（通用功能和数据结构）
├── utils/             # 工具文件（环境检查、Zotero附件定位、图表处理）
├── scripts/           # 工作流脚本（所有核心脚本在此）
├── output/            # 输出文件（Obsidian笔记写入、质量检查）
├── docs/              # 文档和案例报告
├── tmp/               # 临时文件
├── SKILL.md           # 技能配置文件
└── pyproject.toml     # 依赖项配置
```

## 工作流程

### 完整 pipeline（8步）

1. **解析文献**：`resolve_paper.py` — 识别 DOI、arXiv ID 等
2. **收集元数据**：`collect_metadata.py` — 作者、年份、期刊等
3. **获取PDF**：`fetch_pdf.py` — 从本地或网络获取
4. **提取证据**：`extract_evidence.py` — 关键证据和信息
5. **提取资产**：`extract_pdf_assets.py` — 图片资源
6. **规划图表**：`plan_figures.py` — 图表放置规划
7. **构建分析包**：`build_synthesis_bundle.py` — 综合分析包
8. **生成报告**：`write_obsidian_note.py` — 最终 Markdown 报告

### 四阶段教授思维流程（v2.0）

| 阶段 | 耗时 | 定位 |
|------|------|------|
| 信息获取 | 15% | 快速全景把握 |
| 批判性精读 | 40% | 逐节带着问题审视 |
| 跨文献定位 | 25% | 定量基准对比 + 领域定位 |
| 综合评判 | 20% | 生成报告 + 教授总体评价 |

## 使用方法

### 一键分析（推荐）

```bash
# 直接模式 — 提取PDF全文+图片，生成AI写作提示
python scripts/analyze_and_report.py --input "path/to/paper.pdf" --mode direct

# 指定输出目录
python scripts/analyze_and_report.py --input "path/to/paper.pdf" --output-dir "文献分析" --mode direct

# Pipeline模式 — 运行全部8步流程
python scripts/analyze_and_report.py --input "path/to/paper.pdf" --mode pipeline
```

### 分步分析

详见 `scripts/run_pipeline.py`，或参考 `SKILL.md` 中的分步命令。

### 批量分析

```bash
python scripts/batch_analyze.py --input "path/to/pdf_folder/" --output-dir "批量分析结果"
```

### 简易深度报告

```bash
python scripts/simple_deep_report.py --pdf "path/to/paper.pdf"
```

## 安装

```bash
pip install PyMuPDF>=1.24
```

## 关键特性

- **PDF解析**：全文提取 + 图片提取 + 图注自动识别
- **双层分析**：事实提取层 + 批判性分析层
- **教授级评估**：证据强度分级、因果链验证、统计严谨性评估
- **综述Agent接口**：YAML frontmatter + 关键数据提取表 + 创新层级标签
- **Obsidian集成**：结构化笔记输出

详见 `SKILL.md` 获取完整技能说明。
