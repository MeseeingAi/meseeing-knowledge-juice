#!/usr/bin/env python3
"""
📄 论文速读器 —— PDF → 结构化摘要

一条命令，把论文榨成干货。

用法:
    python paper_reader.py path/to/paper.pdf

依赖:
    pip install pymupdf openai

环境变量:
    OPENAI_API_KEY  — OpenAI API Key（必填）

作者:
    密心 (Meseeing) · knowledge-juice
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Optional


# ═══════════════════════════════════════════
# 第一层：PDF 文本提取
# ═══════════════════════════════════════════

def extract_text(pdf_path: str) -> str:
    """
    用 PyMuPDF 从 PDF 里提取纯文本。

    为什么要用这个而不是 pdfplumber / PyPDF2？
    - fitz 速度快，对中文支持好
    - 保留段落结构
    - 跨页段落能自动拼接
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("❌ 请先安装 PyMuPDF: pip install pymupdf")
        sys.exit(1)

    doc = fitz.open(pdf_path)
    pages_text = []

    for page_num, page in enumerate(doc, 1):
        text = page.get_text("text")
        if text.strip():
            pages_text.append(f"--- 第 {page_num} 页 ---\n{text}")

    doc.close()
    return "\n\n".join(pages_text)


# ═══════════════════════════════════════════
# 第二层：智能分块
# ═══════════════════════════════════════════

def smart_chunk(text: str, max_chars: int = 4000) -> list[str]:
    """
    按论文的天然结构做语义分块。

    策略（从粗到细）：
    1. 按 "--- 第 N 页 ---" 标记分页
    2. 每页内按双换行（段落）分
    3. 若段落超长（>max_chars），按句子分
    4. 合并短段落，让每个 chunk 至少 ~500 字
    5. 最终每块不超过 max_chars

    这样分出来的 chunk，语义相对完整，LLM 好理解。
    """
    if not text.strip():
        return []

    # 按段落分（双换行符）
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        # 如果这段本身就超长
        if len(para) > max_chars:
            # 先把当前 chunk 存起来
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""

            # 长段落按句子切
            sentences = para.replace("。", "。\n").replace(".\n", ".\n").split("\n")
            for sent in sentences:
                if len(current_chunk) + len(sent) + 1 > max_chars:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = sent
                else:
                    current_chunk += ("\n" + sent if current_chunk else sent)

        # 正常段落
        elif len(current_chunk) + len(para) + 1 > max_chars:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            current_chunk += ("\n\n" + para if current_chunk else para)

    # 收尾
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


# ═══════════════════════════════════════════
# 第三层：LLM 摘要生成
# ═══════════════════════════════════════════

SUMMARY_PROMPT_TEMPLATE = """你是一个顶级的论文速读助手。

你的任务：从论文片段中提取关键信息，输出结构化摘要。

请从以下维度分析这段文本（如果某些维度在片段中找不到，就填"未提及"）：

1. **研究问题 (Research Problem)**: 这篇论文试图解决什么问题？
2. **方法 (Method)**: 提出了什么方法/模型/框架？
3. **关键发现 (Key Findings)**: 主要实验结果或理论发现。
4. **数据集 (Dataset)**: 用了什么数据？
5. **一句话总结 (One-Sentence Summary)**: 用一句话概括这段的核心内容。

论文片段：
```
{chunk_text}
"""

FINAL_SYNTHESIS_PROMPT = """你是一个顶级的论文速读助手。

以下是一篇论文各个片段的结构化摘要。请将它们合并为一份完整的论文摘要。

输出格式为 Markdown：

```markdown
# 论文摘要：[论文标题]

## 一句话总结
...

## 研究问题
...

## 方法论
...

## 主要发现
...

## 数据集
...

## 局限性
...

## 关键词
- ...
```

各片段摘要：
---
{all_summaries}
---"""


def summarize_chunk(chunk_text: str, client) -> str:
    """调用 LLM 抽取单个 chunk 的结构化摘要"""
    prompt = SUMMARY_PROMPT_TEMPLATE.format(chunk_text=chunk_text[:3500])

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",  # 轻量模型，速度快
            messages=[
                {"role": "system", "content": "你是专业的论文分析助手，输出简洁、结构化。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=800,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"[摘要失败: {e}]"


def synthesize_summaries(all_summaries: str, client) -> str:
    """合并所有 chunk 的摘要为最终报告"""
    prompt = FINAL_SYNTHESIS_PROMPT.format(all_summaries=all_summaries[:12000])

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是专业的论文摘要合并专家。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1500,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"[合并失败: {e}]"


# ═══════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="📄 论文速读器 —— 3分钟榨干一篇论文",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python paper_reader.py paper.pdf
    python paper_reader.py paper.pdf --output summary.md
    python paper_reader.py paper.pdf --model gpt-4o
        """,
    )
    parser.add_argument("pdf", help="PDF 文件路径")
    parser.add_argument("--output", "-o", help="输出文件路径（默认输出到终端）")
    parser.add_argument("--model", default="gpt-4o-mini", help="LLM 模型（默认 gpt-4o-mini）")
    args = parser.parse_args()

    # ── 检查 API Key ──
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ 请设置环境变量 OPENAI_API_KEY")
        print("   export OPENAI_API_KEY='sk-你的key'")
        sys.exit(1)

    # ── 检查 PDF ──
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"❌ 找不到文件: {pdf_path}")
        sys.exit(1)

    print(f"📄 正在读取: {pdf_path.name} ...")

    # 第一层：提取文本
    raw_text = extract_text(str(pdf_path))
    print(f"   ✅ 提取到 {len(raw_text)} 字符")

    # 第二层：智能分块
    chunks = smart_chunk(raw_text)
    print(f"   📦 分为 {len(chunks)} 个语义块")

    # 第三层：逐块摘要
    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    print(f"   🤖 正在逐块分析（{args.model}）...")
    chunk_summaries = []
    for i, chunk in enumerate(chunks, 1):
        print(f"      块 {i}/{len(chunks)}...", end=" ", flush=True)
        summary = summarize_chunk(chunk, client)
        chunk_summaries.append(summary)
        print("✅")

    # 合并摘要
    print("   🔄 正在合并为完整摘要...")
    final_summary = synthesize_summaries(
        "\n\n---\n\n".join(chunk_summaries),
        client,
    )

    # 输出
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(final_summary, encoding="utf-8")
        print(f"\n✅ 摘要已保存到: {output_path}")
    else:
        print("\n" + "=" * 50)
        print(final_summary)
        print("=" * 50)

    print(f"\n📊 统计: {len(chunks)} 块 → 1 份摘要，耗时约 {(len(chunks)) * 3} 秒")


if __name__ == "__main__":
    main()
