#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
"""
PR1 集成测试：使用真实起诉意见书解析数据验证 Schema 扩展功能。

测试数据来源：deepdoc/parser/tests/fixtures/paddleocr_response.json
这是一份真实的起诉意见书（清远市公安局清新分局）的 PaddleOCR 解析结果。

运行方式：
    # 运行所有集成测试
    uv run pytest test/integration/test_pr1_integration.py -v

    # 查看详细输出（包括输入输出对比）
    uv run pytest test/integration/test_pr1_integration.py -v -s

    # 只运行特定场景
    uv run pytest test/integration/test_pr1_integration.py::TestPR1Integration::test_single_block -v -s
"""
import json
import re
from pathlib import Path

import pytest

from rag.nlp import add_positions, add_bbox_union, add_page_range, add_block_refs


# 测试数据路径
FIXTURE_PATH = Path(__file__).parent.parent.parent / "deepdoc" / "parser" / "tests" / "fixtures" / "paddleocr_response.json"


def load_paddleocr_response():
    """加载真实的起诉意见书 PaddleOCR 解析数据。"""
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_blocks(data):
    """
    从 PaddleOCR 响应中提取 blocks。

    返回格式: [(content, tag), ...]
    tag 格式: @@page_num\tleft\tright\ttop\tbottom##
    """
    sections = []
    layout_results = data["result"]["layoutParsingResults"]

    for page_idx, layout_result in enumerate(layout_results):
        blocks = layout_result.get("prunedResult", {}).get("parsing_res_list", [])
        for block in blocks:
            content = block.get("block_content", "").strip()
            if not content:
                continue
            bbox = block.get("block_bbox", [0, 0, 0, 0])
            tag = f"@@{page_idx + 1}\t{bbox[0]}\t{bbox[2]}\t{bbox[1]}\t{bbox[3]}##"
            sections.append((content, tag))

    return sections


def build_chunk_from_blocks(blocks, indices, doc_name="起诉意见书_sample.pdf"):
    """
    从选定的 blocks 构建 chunk，并应用 PR1 的三个扩展函数。

    返回包含 bbox_union, page_range, block_refs 的 chunk 字典。
    """
    chunk = {"docnm_kwd": doc_name}

    # 提取位置信息
    poss = []
    for idx in indices:
        if idx >= len(blocks):
            continue
        content, tag = blocks[idx]
        match = re.search(r"@@(\d+)\t(\d+)\t(\d+)\t(\d+)\t(\d+)##", tag)
        if match:
            page = int(match.group(1)) - 1  # 转为 0-indexed
            left, right = int(match.group(2)), int(match.group(3))
            top, bottom = int(match.group(4)), int(match.group(5))
            poss.append((page, left, right, top, bottom))

    # 应用 PR1 扩展函数
    add_positions(chunk, poss)
    add_bbox_union(chunk)
    add_page_range(chunk)
    add_block_refs(chunk)

    return chunk


@pytest.fixture(scope="module")
def real_data():
    """加载真实起诉意见书数据（模块级别共享）。"""
    return load_paddleocr_response()


@pytest.fixture(scope="module")
def blocks(real_data):
    """提取所有 blocks（模块级别共享）。"""
    return extract_blocks(real_data)


class TestPR1Integration:
    """PR1 集成测试：使用真实起诉意见书数据。"""

    def test_fixture_exists(self):
        """验证测试数据文件存在。"""
        print(f"\n测试数据路径: {FIXTURE_PATH}")
        assert FIXTURE_PATH.exists(), f"测试数据文件不存在: {FIXTURE_PATH}"

    def test_data_overview(self, real_data, blocks):
        """查看数据概览。"""
        layout_results = real_data["result"]["layoutParsingResults"]

        print("\n" + "=" * 60)
        print("真实起诉意见书数据概览")
        print("=" * 60)

        for page_idx, layout_result in enumerate(layout_results):
            page_blocks = layout_result.get("prunedResult", {}).get("parsing_res_list", [])
            print(f"第 {page_idx + 1} 页: {len(page_blocks)} 个 blocks")

        print(f"总 blocks 数: {len(blocks)}")
        print("=" * 60)

        assert len(blocks) > 0, "没有提取到有效的 blocks"

    def test_single_block(self, blocks):
        """场景 1: 单个 block（文档标题）。"""
        print("\n" + "-" * 60)
        print("场景 1: 单个 block")
        print("-" * 60)

        # 选择标题 block
        idx = 2
        content, tag = blocks[idx]

        print(f"输入:")
        print(f"  block[{idx}]")
        print(f"  内容: {content}")
        print(f"  标签: {tag}")

        chunk = build_chunk_from_blocks(blocks, [idx])

        print(f"\n输出:")
        print(f"  bbox_union: {chunk['bbox_union']}")
        print(f"  page_range: {chunk['page_range']}")
        print(f"  block_refs: {chunk['block_refs']}")

        # 验证
        assert chunk["bbox_union"] == [459, 177, 738, 211], "bbox_union 计算错误"
        assert chunk["page_range"] == [1, 1], "page_range 应该是 [1, 1]"
        assert len(chunk["block_refs"]) == 1, "block_refs 应该有 1 个"
        assert chunk["block_refs"][0]["page_index"] == 1

        print("\n✅ 验证通过")

    def test_cross_page_blocks(self, blocks):
        """场景 2: 跨页 blocks。"""
        print("\n" + "-" * 60)
        print("场景 2: 跨页 blocks（第1页末尾 → 第2页开头）")
        print("-" * 60)

        # 选择跨页的 blocks (第1页最后几个 + 第2页开头)
        indices = [15, 16, 17, 18]

        print("输入:")
        for idx in indices:
            if idx < len(blocks):
                content, tag = blocks[idx]
                page_match = re.search(r"@@(\d+)", tag)
                page = page_match.group(1) if page_match else "?"
                print(f"  block[{idx}] (第{page}页): {content[:40]}...")

        chunk = build_chunk_from_blocks(blocks, indices)

        print(f"\n输出:")
        print(f"  bbox_union: {chunk['bbox_union']}")
        print(f"  page_range: {chunk['page_range']} ← 跨页标识")
        print(f"  block_refs 数量: {len(chunk['block_refs'])}")

        # 验证跨页
        assert chunk["page_range"][0] < chunk["page_range"][1], "应该识别为跨页"
        assert chunk["page_range"] == [1, 2], "page_range 应该是 [1, 2]"

        print("\n✅ 验证通过 - 正确识别跨页")

    def test_full_document(self, blocks):
        """场景 3: 完整文档（所有 blocks）。"""
        print("\n" + "-" * 60)
        print("场景 3: 完整文档")
        print("-" * 60)

        all_indices = list(range(len(blocks)))

        print(f"输入:")
        print(f"  总 blocks 数: {len(blocks)}")

        chunk = build_chunk_from_blocks(blocks, all_indices)

        print(f"\n输出:")
        print(f"  bbox_union: {chunk['bbox_union']} ← 整个文档边界框")
        print(f"  page_range: {chunk['page_range']} ← 文档页码范围")
        print(f"  block_refs 数量: {len(chunk['block_refs'])}")

        # 验证
        assert chunk["page_range"] == [1, 2], "文档应该跨 2 页"
        assert len(chunk["block_refs"]) == len(blocks), "block_refs 数量应该等于 blocks 数量"

        print("\n✅ 验证通过")

    def test_json_serialization(self, blocks):
        """场景 4: JSON 序列化验证。"""
        print("\n" + "-" * 60)
        print("场景 4: JSON 序列化")
        print("-" * 60)

        all_indices = list(range(len(blocks)))
        chunk = build_chunk_from_blocks(blocks, all_indices)

        # 序列化
        json_str = json.dumps(chunk, ensure_ascii=False, indent=2)
        json_size = len(json_str)

        print(f"序列化后大小: {json_size} 字节")
        print(f"\nJSON 预览 (前 500 字符):")
        print(json_str[:500] + "...")

        # 反序列化验证
        parsed = json.loads(json_str)

        assert parsed["bbox_union"] == chunk["bbox_union"], "bbox_union 序列化后不一致"
        assert parsed["page_range"] == chunk["page_range"], "page_range 序列化后不一致"
        assert parsed["block_refs"] == chunk["block_refs"], "block_refs 序列化后不一致"

        print("\n✅ 验证通过 - JSON 序列化/反序列化正常")

    def test_block_refs_detail(self, blocks):
        """场景 5: block_refs 详细验证。"""
        print("\n" + "-" * 60)
        print("场景 5: block_refs 详细验证")
        print("-" * 60)

        # 选择前 5 个 blocks
        indices = list(range(5))
        chunk = build_chunk_from_blocks(blocks, indices)

        print("输入 blocks:")
        for i, idx in enumerate(indices):
            content, tag = blocks[idx]
            print(f"  [{idx}] {content[:30]}...")

        print(f"\n输出 block_refs:")
        for i, ref in enumerate(chunk["block_refs"]):
            print(f"  [{i}] page_index={ref['page_index']}, block_id={ref['block_id']}")

        # 验证每个 block_ref 的结构
        for ref in chunk["block_refs"]:
            assert "page_index" in ref, "block_ref 缺少 page_index"
            assert "block_id" in ref, "block_ref 缺少 block_id"
            assert isinstance(ref["page_index"], int), "page_index 应该是整数"
            assert isinstance(ref["block_id"], str), "block_id 应该是字符串"

        print("\n✅ 验证通过 - block_refs 结构正确")


class TestPR1DataIntegrity:
    """PR1 数据完整性测试。"""

    def test_bbox_union_coordinates_valid(self, blocks):
        """验证 bbox_union 坐标有效（x1 < x2, y1 < y2）。"""
        all_indices = list(range(len(blocks)))
        chunk = build_chunk_from_blocks(blocks, all_indices)

        x1, y1, x2, y2 = chunk["bbox_union"]

        print(f"\nbbox_union: [{x1}, {y1}, {x2}, {y2}]")
        print(f"  宽度: {x2 - x1} 像素")
        print(f"  高度: {y2 - y1} 像素")

        assert x1 < x2, f"x1({x1}) 应该小于 x2({x2})"
        assert y1 < y2, f"y1({y1}) 应该小于 y2({y2})"
        assert x1 >= 0 and y1 >= 0, "坐标应该非负"

        print("✅ bbox_union 坐标有效")

    def test_page_range_order_valid(self, blocks):
        """验证 page_range 顺序有效（start <= end）。"""
        # 测试多种组合
        test_cases = [
            [0],           # 单个 block
            [0, 1, 2],     # 同页多个
            [15, 16, 17],  # 跨页
            list(range(len(blocks))),  # 全部
        ]

        for indices in test_cases:
            chunk = build_chunk_from_blocks(blocks, indices)
            start, end = chunk["page_range"]
            assert start <= end, f"page_range[{start}, {end}] 顺序无效"

        print("✅ 所有 page_range 顺序有效")

    def test_block_refs_count_matches(self, blocks):
        """验证 block_refs 数量与输入 blocks 数量匹配。"""
        for count in [1, 5, 10, len(blocks)]:
            indices = list(range(count))
            chunk = build_chunk_from_blocks(blocks, indices)
            assert len(chunk["block_refs"]) == count, \
                f"block_refs 数量 {len(chunk['block_refs'])} 与输入 {count} 不匹配"

        print(f"✅ block_refs 数量与输入匹配 (测试了 1, 5, 10, {len(blocks)})")


# ============================================================
# 独立运行脚本：直接查看输入输出对比
# ============================================================

if __name__ == "__main__":
    """
    直接运行此文件查看详细的输入输出对比：

        uv run python test/integration/test_pr1_integration.py

    输出示例：
        ============================================================
        PR1 集成测试：使用真实起诉意见书解析数据
        ============================================================
        测试数据: deepdoc/parser/tests/fixtures/paddleocr_response.json
        总 blocks: 24 个

        ------------------------------------------------------------
        场景 1: 单个 block
        ------------------------------------------------------------
        输入:
          block[2]: 清远市公安局清新分局
        输出:
          bbox_union: [459, 177, 738, 211]
          page_range: [1, 1]
          block_refs: [{'page_index': 1, 'block_id': 'p1_0'}]
        ✅ 验证通过
        ...
    """
    print("=" * 60)
    print("PR1 集成测试：使用真实起诉意见书解析数据")
    print("=" * 60)

    # 加载数据
    print(f"\n测试数据: {FIXTURE_PATH}")
    data = load_paddleocr_response()
    blocks = extract_blocks(data)
    print(f"总 blocks: {len(blocks)} 个")

    # 运行所有场景
    test = TestPR1Integration()

    print("\n" + "=" * 60)
    test.test_single_block(blocks)

    print("\n" + "=" * 60)
    test.test_cross_page_blocks(blocks)

    print("\n" + "=" * 60)
    test.test_full_document(blocks)

    print("\n" + "=" * 60)
    test.test_json_serialization(blocks)

    print("\n" + "=" * 60)
    test.test_block_refs_detail(blocks)

    print("\n" + "=" * 60)
    print("PR1 集成测试完成：全部通过 ✅")
    print("=" * 60)
