#!/usr/bin/env python3
"""
本地测试：直接解析讯问笔录 PDF 并检查 chunk 顺序
"""

import logging
import sys
import re
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 只显示 interrogation_plugin 的 DEBUG 日志
logging.getLogger('rag.app.criminal.plugins.interrogation_plugin').setLevel(logging.DEBUG)
# 减少其他模块的噪音
for name in ['httpcore', 'LiteLLM', 'httpx', 'urllib3', 'asyncio']:
    logging.getLogger(name).setLevel(logging.WARNING)


def test_interrogation_parsing():
    """测试讯问笔录解析 - 直接使用 interrogation chunk 函数"""
    from rag.app.interrogation import chunk
    from pathlib import Path

    # 找到样本 PDF
    sample_dir = Path("/home/you/cs/proj/Superyou/SampleData/interrogation")
    pdf_files = list(sample_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {sample_dir}")
        return

    pdf_path = pdf_files[0]  # 使用第一个 PDF
    print(f"Testing with: {pdf_path}")
    print("=" * 60)

    # 读取文件
    with open(pdf_path, 'rb') as f:
        binary = f.read()

    # 回调函数 - 需要支持两种签名
    progress_messages = []
    def callback(progress_or_msg, msg=None):
        if msg is None:
            # 旧签名: callback(msg)
            print(f"[MSG] {progress_or_msg}")
        else:
            # 新签名: callback(progress, msg)
            progress_messages.append((progress_or_msg, msg))
            print(f"[{progress_or_msg:.0%}] {msg}")

    # 解析 - 使用 DeepDOC 解析器
    try:
        chunks = chunk(
            filename=pdf_path.name,
            binary=binary,
            from_page=0,
            to_page=100,
            lang="Chinese",
            callback=callback,
            parser_config={
                "layout_recognize": "DeepDOC",  # 使用 DeepDOC 解析器
            }
        )

        print("\n" + "=" * 60)
        print(f"解析完成，共 {len(chunks)} 个 chunks")
        print("=" * 60)

        # 检查 chunk 顺序
        print("\nChunk 顺序:")
        for i, c in enumerate(chunks):
            content = c.get('content_with_weight', '')[:80]
            # 判断 chunk 类型
            if '问：' in content or '答：' in content:
                chunk_type = 'qa_pair'
            else:
                chunk_type = 'header_info'
            print(f"  [{i}] {chunk_type}: {content}...")

        # 验证顺序
        print("\n" + "=" * 60)
        print("验证结果:")
        if chunks:
            first_content = chunks[0].get('content_with_weight', '')
            if '问：' in first_content and '讯问笔录' not in first_content:
                print("❌ 问题：第一个 chunk 是 QA，应该先有 header_info")
            else:
                print("✓ 第一个 chunk 不是纯 QA")
        print("=" * 60)

        return chunks

    except Exception as e:
        print(f"解析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    test_interrogation_parsing()
