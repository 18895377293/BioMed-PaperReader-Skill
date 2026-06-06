---
名称: 满满文献阅读器
版本: v2.0 — 批判性精读版
描述: 基于Python脚本体系，将一篇研究论文深度解析为结构化Obsidian笔记/深度阅读报告。支持PDF全文提取、批判性分析、综述Agent接口（YAML frontmatter + 改写式关键论证引用 + 关键数据提取表）
作者: 满满
---

# 文献阅读器技能分类与工作流

## 目录结构

```
文献阅读器/
├── core/                          # 核心文件
│   ├── common.py                  # 通用功能和工具函数
│   └── contracts.py               # 数据结构和接口定义
├── utils/                         # 工具文件
│   ├── check_environment.py       # 环境检查
│   ├── locate_zotero_attachment.py # Zotero附件定位
│   └── materialize_figure_asset.py # 图表资产处理
├── scripts/                       # 工作流脚本（所有核心脚本在此）
│   ├── analyze_and_report.py      # 一键分析并生成报告（含pipeline/direct双模式）
│   ├── batch_analyze.py           # 批量分析多篇文献
│   ├── run_pipeline.py            # 运行完整分析pipeline（8步流程）
│   ├── build_synthesis_bundle.py  # 构建综合分析包
│   ├── collect_metadata.py        # 收集文献元数据
│   ├── create_input_record.py     # 创建输入记录
│   ├── extract_evidence.py        # 提取关键证据
│   ├── extract_pdf_assets.py      # 提取PDF图片资源
│   ├── fetch_pdf.py               # 获取PDF文件
│   ├── plan_figures.py            # 规划图表放置
│   ├── resolve_paper.py           # 解析文献身份
│   ├── simple_deep_report.py      # 简易深度报告生成器
│   ├── common.py                  # 脚本层通用函数（独立副本）
│   └── contracts.py               # 脚本层数据接口（独立副本）
├── output/                        # 输出文件
│   ├── write_obsidian_note.py     # 写入Obsidian笔记
│   └── lint_note.py               # 检查笔记质量
├── docs/                          # 文档
│   ├── README.md                  # 使用说明
│   ├── CHANGELOG.md               # 版本更新日志
│   ├── 案例报告_ePOWER.md         # 案例报告
│   └── 案例报告_序贯超声巨噬细胞.md # 案例报告
├── tmp/                           # 临时文件
│   └── LiteratureReader_runs/     # 运行记录
├── SKILL.md                       # 本技能配置文件
└── pyproject.toml                 # 依赖项（PyMuPDF>=1.24）
```

## v2.0 核心升级

### 思维升级

从"信息提取+评论"升级为**带着批判眼光审视**：这篇论文有多可信？创新在哪里？对后续研究有什么实质帮助？

### v2.0 报告结构（17章）

```
YAML Frontmatter（放在报告末尾，引用之后，供综述Agent机读解析）
  │
  ├─ 1. 核心信息
  ├─ 2. 原文摘要翻译
  ├─ 3. 创新点（含创新层级标签）
  ├─ 4. 一句话总结
  ├─ 5. 研究问题
  ├─ 6. 数据与任务定义
  ├─ 7. 方法主线
  ├─ 8. 关键结果（注明对应Figure，不嵌入图片）
  ├─ 9. 深度分析
  │   ├─ 定量基准对比（与领域内代表性文献做对比表）
  │   ├─ 机制解析
  │   └─ 统计严谨性与效应量评估
  ├─ 10. 综合批判性讨论   ← ★重构
  │   ├─ 证据强度与局限性
  │   ├─ 数据交叉验证与替代解释
  │   ├─ 领域定位与可复现性
  │   ├─ 未解答开放问题
  │   └─ 研究的创新性、重要性、可行性深度思考
  ├─ 11. 研究启发
  ├─ 12. 综述Agent写作参考  ← ★新增
  │   ├─ 关键论证引用（改写式，非原文复制）
  │   └─ 文献贡献定位（适合/不适合的综述场景）
  ├─ 13. 关键数据提取表
  └─ 14. 引用
```

### 各章节内容要求

#### 1-8章：事实层（客观呈现论文说了什么）
与v1.2保持一致，但关键结果部分**不嵌入图片**，改为文字指明对应关系：
- 格式：`→ 对应 Figure 3A-C（体内治疗效果评估）`
- 图片单独存放在 `figures/` 目录下

#### 9. 深度分析
三个核心方面，每个1-2段：

- **定量基准对比**：与领域内2-3篇代表性文献做对比表，明确标注超越/持平/不如
- **机制解析**：从分子机制到表型输出的完整链条
- **统计严谨性与效应量**：检查多重比较校正、效应量报告、样本量，每个显著结果的效应量实际意义

#### 10. 综合批判性讨论（★核心新增）
将原本分散的8个批判性维度合并为一个完整讨论段落，按逻辑递进排列：

```
【证据强度与局限性】
对核心结论做强/中/弱分级，逐条列出局限性及其影响程度

【数据交叉验证与替代解释】
检查不同指标间定量关系是否自洽，主动探讨作者未排除的解释

【领域定位与可复现性】
放在领域脉络中评估是突破还是增量；检查数据/代码/试剂公开情况

【未解答开放问题】
全领域共同的认知空白（与局限性区分：局限性=这篇没做好，开放问题=全领域没回答）

【创新性·重要性·可行性深度思考】
从三个维度综合评判：
- 创新性：真创新还是换包装？解决了什么实质难题？
- 重要性：如果结论成立，对领域有什么实质推动？
- 可行性：转化成应用或后续研究的门槛有多高？
```

#### 11. 研究启发
对后续研究的具体启发点（不变）

#### 12. 综述Agent写作参考（★核心新增）
**关键论证引用（1-3段，改写式）：**

每段浓缩一个核心论点，用**非原文的语言**重述，附带具体效应量和关键数据，让Agent可以直接粘贴到综述正文中使用。

格式：
```
【论点1：XXXX】
改写式论证段落（约3-5句，包含证据链和关键数据，不直接引用原文）

【论点2：XXXX】
改写式论证段落

【论点3：XXXX】
...
```

**文献贡献定位（1-2句）：**
- 这篇文献最适合支撑综述中哪个论点
- 不适合用于什么场景（避免错误引用）

#### 13. 关键数据提取表
标准化表格，综述Agent可直接提取效应量做定量对比

#### 14. 引用
标准引用格式

### AI工作流程（4阶段）

| 阶段 | 耗时 | 思维指引 |
|------|------|---------|
| 信息获取 | 15% | 通读摘要、引言末段、结果图表、讨论首段，快速把握全景 |
| 批判性精读 | 40% | 逐节带着问题：方法合理吗？结论被数据支撑吗？缺什么对照？ |
| 综合分析 | 25% | 横向对比同类文献，前后验证数据一致性，评估证据强度 |
| 写作输出 | 20% | 按17章结构生成报告，重点完成综合讨论和综述参考 |

### 质量要求

**五项原则：**
- **不盲从**：作者结论不等于事实，用自己的判断
- **定量优先**：能用数字说话就不用形容词
- **证据链审视**：逐环检查每个论证的逻辑链条
- **透明标注**：区分"论文明确说"vs"我的推断"vs"我不确定"
- **服务综述**：笔记最终服务于综述Agent，每个数据要可被直接引用

**必做检查：**
- ✅ 每个核心结论标注证据等级
- ✅ 每个显著结果讨论效应量实际意义
- ✅ 主动寻找并讨论替代解释
- ✅ 定量基准对比至少2篇文献
- ✅ 综述参考段落必须是改写式，不能是原文摘抄
- ❌ 禁止"意义重大/有趣"这类模糊表述
- ❌ 禁止只做描述不做判断
- ❌ 禁止忽略数据矛盾

## 使用方法

### 一键分析（推荐）

```bash
# 直接提取PDF全文 + 图片 + 生成AI写作提示模板
python scripts/analyze_and_report.py --input "path/to/paper.pdf" --mode direct

# 指定输出目录
python scripts/analyze_and_report.py --input "path/to/paper.pdf" \
    --output-dir "文献分析" --mode direct

# 运行完整pipeline（8步：解析→元数据→PDF→证据→资产→图表→分析包→报告）
python scripts/analyze_and_report.py --input "path/to/paper.pdf" --mode pipeline
```

### 分步分析（高级用户）

```bash
# 1. 解析文献
python scripts/resolve_paper.py --input "path/to/paper.pdf" --output "tmp/LiteratureReader_runs/run_resolve.json"

# 2. 收集元数据
python scripts/collect_metadata.py --input "path/to/paper.pdf" --output "tmp/LiteratureReader_runs/run_metadata.json"

# 3. 获取PDF
python scripts/fetch_pdf.py --input "path/to/paper.pdf" --output "tmp/LiteratureReader_runs/run_fetch.json"

# 4. 提取证据
python scripts/extract_evidence.py --input "tmp/LiteratureReader_runs/run_fetch.json" --output "tmp/LiteratureReader_runs/run_evidence.json"

# 5. 提取资产
python scripts/extract_pdf_assets.py --input "tmp/LiteratureReader_runs/run_fetch.json" --output "tmp/LiteratureReader_runs/run_assets.json"

# 6. 规划图表
python scripts/plan_figures.py --evidence "tmp/LiteratureReader_runs/run_evidence.json" --assets "tmp/LiteratureReader_runs/run_assets.json" --output "tmp/LiteratureReader_runs/run_figures.json"

# 7. 构建分析包
python scripts/build_synthesis_bundle.py \
    --metadata "tmp/LiteratureReader_runs/run_metadata.json" \
    --evidence "tmp/LiteratureReader_runs/run_evidence.json" \
    --figures "tmp/LiteratureReader_runs/run_figures.json" \
    --assets "tmp/LiteratureReader_runs/run_assets.json" \
    --output "tmp/LiteratureReader_runs/run_bundle.json"

# 8. 生成报告
python output/write_obsidian_note.py --input "tmp/LiteratureReader_runs/run_bundle.json" --title "文献标题"
```

### 批量分析

```bash
python scripts/batch_analyze.py --input "path/to/pdf_folder/" --output-dir "批量分析结果"
```

### 简易深度报告

```bash
python scripts/simple_deep_report.py --pdf "path/to/paper.pdf"
```

## 环境要求

- Python >= 3.10
- PyMuPDF >= 1.24（PDF文本和图片提取）
- Obsidian（可选，用于笔记输出）

### 安装

```bash
pip install PyMuPDF>=1.24
```

## 配置选项

可通过 `deep_paper_note_config.json` 配置文件（当前目录 / `~/.deep_paper_note_config.json` / `~/.config/deep_paper_note/config.json`）设置：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| obsidian_vault | Obsidian库路径 | - |
| papers_dir | 文献存储目录 | - |
| output_dir | 输出目录 | tmp/LiteratureReader |
| cache_dir | 缓存目录 | tmp/LiteratureReader_cache |
| cache_enabled | 是否启用缓存 | true |
| cache_ttl | 缓存过期时间（秒） | 86400 |
| max_workers | 并行数 | 5 |
| timeout | 超时（秒） | 30 |

### 环境变量

- `LiteratureReader_OBSIDIAN_VAULT`：Obsidian库路径
- `LiteratureReader_PAPERS_DIR`：文献存储目录
- `LiteratureReader_OUTPUT_DIR`：输出目录
- `LiteratureReader_CACHE_DIR`：缓存目录
- `LiteratureReader_CACHE_ENABLED`：是否启用缓存
- `LiteratureReader_CACHE_TTL`：缓存过期时间

## 输出规范

### 图片引用规则
- 支持子图级命名和引用（如Figure 3A-M可拆分到子图级别）
- 图片文件名后可附加类型标签，如 `Figure1_示意图.png`、`Figure2_统计图.png`、`Figure3E_电镜.png`
- 在关键结果部分按正文逻辑（非Figure编号机械顺序）匹配插入

### YAML Frontmatter格式（放在报告末尾，引用之后）

放在报告末尾，用 `---` 包裹：
```yaml
---
paper_id: "PMID/DOI"
year: 2025
journal: "Nature Communications"
research_type: "experimental"
field: "nanomedicine"
subfield: "cancer immunotherapy"
cell_types: ["DC2.4", "RAW264.7", "BMDCs"]
animal_model: "C57BL/6"
key_techniques: ["flow cytometry", "TEM", "ELISA"]
effect_size_summary: "treatment group showed 3.2x increase vs control"
tags:
  concepts: ["sonodynamic therapy", "immunogenic cell death"]
  methods: ["lipid nanoparticle", "ultrasound"]
  findings: ["STING pathway activation", "DC maturation"]
---
```

### 关键数据提取表格式
| 指标 | 对照组 | 实验组 | 效应量 | 显著性 | n |
|------|--------|--------|--------|--------|---|
| DC maturation (%) | 15.2±3.1 | 48.7±5.2 | 3.2x | p<0.001 | 6 |

严格原则：只填论文明确给出的数据，不推测。

### 创新层级评估标签
- 【颠覆性创新】— 开创新范式
- 【重要机制发现】— 揭示关键分子机制
- 【增量改进】— 在已有方法上提升性能
- 【方法学创新】— 新技术/新工具
- 【应用创新】— 已有方法应用于新场景

## 版本历史

| 版本 | 日期 | 核心变化 |
|------|------|----------|
| v2.0 | 2026-05-07 | 批判性精读版：17章报告结构、合并批判性维度为综合讨论、新增「综述Agent写作参考」（改写式关键论证+文献贡献定位）、去掉图片嵌入改为文字对应、新增创新性/重要性/可行性深度思考 |
| v1.4 | 2026-05-06 | 综述Agent接口版：YAML frontmatter、关键数据提取表、创新层级评估标签 |
| v1.3 | 2026-05-06 | 批判性分析体系：证据强度评估、数据交叉验证、替代解释、领域定位、可复现性 |
| v1.2 | - | 初始版本：12章报告结构、8步pipeline流程 |

详见 `docs/CHANGELOG.md`
