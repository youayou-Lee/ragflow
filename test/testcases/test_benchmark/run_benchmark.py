#!/usr/bin/env python3
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
"""
PR7 Benchmark 检索测试运行脚本

使用方法:
    uv run python test/testcases/test_benchmark/run_benchmark.py

环境变量:
    RAGFLOW_HOST: RAGFlow 服务地址 (默认: http://localhost:9380)
    RAGFLOW_API_KEY: API Token (从 api_token 表获取)

该脚本会:
1. 从 benchmark/ 目录读取 JSON 数据和测试题目
2. 使用 API 创建数据集并上传文档（从 JSON 提取文本）
3. 运行检索测试
4. 生成测试报告
"""
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests

# 配置
RAGFLOW_HOST = os.getenv("RAGFLOW_HOST", "http://localhost:9380")
API_KEY = os.getenv("RAGFLOW_API_KEY", "")

# 题库路径
BENCHMARK_DIR = Path(__file__).parent.parent.parent.parent / "benchmark"


@dataclass
class Question:
    """测试题目"""
    number: int
    topic: str
    question: str
    answer: str
    evidence: str
    qtype: str  # factual, evidence, conflict


def extract_text_from_paddlevl_json(json_path: Path) -> str:
    """从 PaddleVL JSON 提取文本内容"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    texts = []

    # 尝试不同的数据结构
    # 结构1: result.layoutParsingResults (起诉意见书)
    result = data.get('result', {})
    layout_results = result.get('layoutParsingResults', [])

    # 结构2: layoutParsingResults 顶层 (讯问笔录)
    if not layout_results:
        layout_results = data.get('layoutParsingResults', [])

    for page in layout_results:
        # 从 markdown 字段提取
        md = page.get('markdown', {})
        text = md.get('text', '')
        if text:
            texts.append(text)

    return '\n\n'.join(texts)


def parse_questions(md_path: Path, qtype: str) -> list[Question]:
    """解析 Markdown 题目文件"""
    content = md_path.read_text(encoding='utf-8')
    questions = []

    # 匹配题目格式
    pattern = r"## (\d+)\.\s+(.+?)\n\n\*\*问题\*\*[：:]\s*(.+?)\n\n\*\*答案\*\*[：:]\s*(.+?)(?=\n\n\*\*位置\*\*|\n\n---)"
    matches = re.findall(pattern, content, re.DOTALL)

    for match in matches:
        questions.append(Question(
            number=int(match[0]),
            topic=match[1].strip(),
            question=match[2].strip(),
            answer=match[3].strip(),
            evidence="",
            qtype=qtype
        ))

    return questions


class RAGFlowClient:
    """RAGFlow API 客户端"""

    def __init__(self, host: str, api_key: str):
        self.host = host.rstrip('/')
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def create_dataset(self, name: str, embedding_model: str = "embedding-3@ZHIPU-AI") -> dict:
        """创建数据集"""
        url = f"{self.host}/api/v1/datasets"
        resp = requests.post(url, headers=self.headers, json={
            "name": name,
            "embedding_model": embedding_model
        })
        return resp.json()

    def delete_dataset(self, dataset_id: str) -> dict:
        """删除数据集"""
        url = f"{self.host}/api/v1/datasets"
        resp = requests.delete(url, headers=self.headers, json={"ids": [dataset_id]})
        return resp.json()

    def upload_document(self, dataset_id: str, file_path: Path) -> dict:
        """上传文档"""
        url = f"{self.host}/api/v1/datasets/{dataset_id}/documents"
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f, 'text/plain')}
            resp = requests.post(url, headers=self.headers, files=files)
        return resp.json()

    def parse_documents(self, dataset_id: str, document_ids: list[str]) -> dict:
        """解析文档"""
        url = f"{self.host}/api/v1/datasets/{dataset_id}/chunks"
        resp = requests.post(url, headers=self.headers, json={
            "document_ids": document_ids
        })
        return resp.json()

    def list_documents(self, dataset_id: str) -> dict:
        """列出文档"""
        url = f"{self.host}/api/v1/datasets/{dataset_id}/documents"
        resp = requests.get(url, headers=self.headers)
        return resp.json()

    def retrieval(self, question: str, dataset_ids: list[str], top_k: int = 10) -> dict:
        """检索"""
        url = f"{self.host}/api/v1/retrieval"
        resp = requests.post(url, headers=self.headers, json={
            "question": question,
            "dataset_ids": dataset_ids,
            "top_k": top_k,
            "page": 1,
            "page_size": top_k
        })
        return resp.json()

    def wait_for_parsing(self, dataset_id: str, document_ids: list[str], timeout: int = 120) -> bool:
        """等待解析完成"""
        start = time.time()
        while time.time() - start < timeout:
            resp = self.list_documents(dataset_id)
            if resp.get("code") == 0:
                docs = resp.get("data", {}).get("docs", [])
                target_ids = set(document_ids)
                done_ids = set()
                for doc in docs:
                    if doc.get("id") in target_ids and doc.get("run") == "DONE":
                        done_ids.add(doc.get("id"))
                if done_ids == target_ids:
                    return True
            time.sleep(2)
        return False


def check_factual_answer(answer: str, chunks: list[dict]) -> tuple[bool, str]:
    """检查事实型题目答案"""
    answer_lower = answer.lower().strip()
    for i, chunk in enumerate(chunks):
        content = chunk.get("content", "").lower()
        if answer_lower in content:
            return True, f"在 chunk {i+1} 中找到 (相似度: {chunk.get('similarity', 'N/A'):.3f})"
    return False, f"答案 '{answer}' 未在检索结果中找到"


def check_evidence_answer(answer: str, chunks: list[dict]) -> tuple[bool, str]:
    """检查证据集合型题目"""
    lines = [l.strip() for l in answer.split('\n') if l.strip()]
    found = 0
    missing = []

    for line in lines:
        key = re.sub(r"^\d+\.\s*", "", line)
        key = re.sub(r"\*\*[^*]+\*\*[：:]\s*", "", key).strip()
        if not key or len(key) < 3:
            continue

        for chunk in chunks:
            if key.lower() in chunk.get("content", "").lower():
                found += 1
                break
        else:
            missing.append(key[:30])

    total = len([l for l in lines if len(l.strip()) > 3])
    if found >= total:
        return True, f"所有 {found} 项证据已找到"
    elif found > 0:
        return False, f"部分匹配: {found}/{total}，缺失: {missing[:2]}"
    return False, "未找到任何证据项"


def check_conflict_answer(chunks: list[dict]) -> tuple[bool, str]:
    """检查冲突缺口型题目"""
    # 对于冲突型题目，如果检索结果的相似度都很低，说明系统正确识别了信息缺失
    if not chunks:
        return True, "正确识别为缺失信息（无检索结果）"

    # 检查最高相似度
    max_sim = max(c.get("similarity", 0) for c in chunks)
    if max_sim < 0.3:
        return True, f"正确识别为缺失信息（最高相似度: {max_sim:.3f}）"
    return False, f"可能找到相关内容（最高相似度: {max_sim:.3f}），需人工验证"


def run_benchmark_test():
    """运行 Benchmark 测试"""
    if not API_KEY:
        print("错误: 请设置 RAGFLOW_API_KEY 环境变量")
        print("可以从数据库获取: SELECT token FROM api_token LIMIT 1;")
        return

    client = RAGFlowClient(RAGFLOW_HOST, API_KEY)

    # 收集所有案例
    cases = []
    for case_type_dir in BENCHMARK_DIR.iterdir():
        if not case_type_dir.is_dir():
            continue
        for case_dir in case_type_dir.iterdir():
            if not case_dir.is_dir():
                continue

            # 读取 JSON 数据（优先使用 paddleocr_response.json）
            json_files = list((case_dir / "原始数据").glob("*.json"))
            if not json_files:
                continue

            # 优先选择 paddleocr_response.json
            json_path = None
            for jf in json_files:
                if jf.name == "paddleocr_response.json":
                    json_path = jf
                    break
            if not json_path:
                json_path = json_files[0]

            # 读取题目
            questions = []
            for qtype, filename in [("factual", "01-事实型题目.md"),
                                     ("evidence", "02-证据集合型题目.md"),
                                     ("conflict", "03-冲突缺口型题目.md")]:
                qfile = case_dir / filename
                if qfile.exists():
                    questions.extend(parse_questions(qfile, qtype))

            cases.append({
                "name": case_dir.name,
                "type": case_type_dir.name,
                "json_path": json_path,
                "questions": questions
            })

    print(f"发现 {len(cases)} 个测试案例")
    for case in cases:
        print(f"  - {case['type']}/{case['name']}: {len(case['questions'])} 题")

    # 测试结果
    all_results = []

    for case in cases:
        print(f"\n{'='*60}")
        print(f"测试案例: {case['type']} - {case['name']}")
        print(f"{'='*60}")

        # 提取文本
        text = extract_text_from_paddlevl_json(case["json_path"])
        if not text:
            print(f"  警告: 无法从 JSON 提取文本")
            continue

        # 保存临时文件
        tmp_file = Path(f"/tmp/benchmark_{case['name']}.txt")
        tmp_file.write_text(text, encoding='utf-8')

        # 创建数据集
        dataset_name = f"benchmark_{case['name']}_{int(time.time())}"
        print(f"  创建数据集: {dataset_name}")
        resp = client.create_dataset(dataset_name)
        if resp.get("code") != 0:
            print(f"  错误: 创建数据集失败 - {resp}")
            continue

        dataset_id = resp["data"]["id"]
        print(f"  数据集 ID: {dataset_id}")

        try:
            # 上传文档
            print(f"  上传文档...")
            resp = client.upload_document(dataset_id, tmp_file)
            if resp.get("code") != 0:
                print(f"  错误: 上传文档失败 - {resp}")
                continue

            doc_ids = [d["id"] for d in resp["data"]]
            print(f"  文档 ID: {doc_ids}")

            # 解析文档
            print(f"  解析文档...")
            resp = client.parse_documents(dataset_id, doc_ids)
            if resp.get("code") != 0:
                print(f"  错误: 启动解析失败 - {resp}")
                continue

            # 等待解析完成
            print(f"  等待解析完成...")
            if not client.wait_for_parsing(dataset_id, doc_ids, timeout=60):
                print(f"  警告: 解析超时")
                continue

            print(f"  解析完成!")

            # 运行检索测试
            case_results = {"factual": [], "evidence": [], "conflict": []}

            for q in case["questions"]:
                print(f"\n  Q{q.number} [{q.qtype}]: {q.question[:50]}...")

                # 调用检索 API
                resp = client.retrieval(q.question, [dataset_id], top_k=10)
                if resp.get("code") != 0:
                    print(f"    错误: 检索失败 - {resp.get('message')}")
                    continue

                chunks = resp.get("data", {}).get("chunks", [])
                print(f"    检索到 {len(chunks)} 个 chunks")

                # 评估结果
                if q.qtype == "factual":
                    passed, reason = check_factual_answer(q.answer, chunks)
                elif q.qtype == "evidence":
                    passed, reason = check_evidence_answer(q.answer, chunks)
                else:  # conflict
                    passed, reason = check_conflict_answer(chunks)

                status = "✅" if passed else "❌"
                print(f"    {status} {reason}")

                case_results[q.qtype].append({
                    "question": q,
                    "passed": passed,
                    "reason": reason,
                    "chunks_count": len(chunks)
                })

            all_results.append({
                "case": case,
                "results": case_results
            })

        finally:
            # 清理数据集
            print(f"\n  清理数据集...")
            client.delete_dataset(dataset_id)
            tmp_file.unlink(missing_ok=True)

    # 生成报告
    generate_report(all_results)


def generate_report(all_results: list):
    """生成测试报告"""
    report_path = Path(__file__).parent / "RESULTS.md"

    lines = [
        "# Benchmark 检索测试报告",
        "",
        f"**测试日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**RAGFlow 版本**: main",
        f"**Embedding 模型**: embedding-3@ZHIPU-AI",
        "",
        "---",
        ""
    ]

    # 统计
    total_stats = {"factual": {"passed": 0, "total": 0},
                   "evidence": {"passed": 0, "total": 0},
                   "conflict": {"passed": 0, "total": 0}}

    for result in all_results:
        case = result["case"]
        results = result["results"]

        lines.extend([
            f"## {case['type']} - {case['name']}",
            ""
        ])

        for qtype, qname in [("factual", "事实型题目"), ("evidence", "证据集合型题目"), ("conflict", "冲突缺口型题目")]:
            qresults = results.get(qtype, [])
            if not qresults:
                continue

            passed = sum(1 for r in qresults if r["passed"])
            total = len(qresults)
            total_stats[qtype]["passed"] += passed
            total_stats[qtype]["total"] += total

            lines.extend([
                f"### {qname}（{total}题）",
                "",
                "| # | 问题 | 预期答案 | 状态 | 原因 |",
                "|---|------|----------|------|------|"
            ])

            for r in qresults:
                q = r["question"]
                status = "✅" if r["passed"] else "❌"
                q_short = q.question[:30] + "..." if len(q.question) > 30 else q.question
                a_short = q.answer[:20] + "..." if len(q.answer) > 20 else q.answer
                r_short = r["reason"][:35] + "..." if len(r["reason"]) > 35 else r["reason"]
                lines.append(f"| {q.number} | {q_short} | {a_short} | {status} | {r_short} |")

            lines.extend([
                "",
                f"**通过率: {passed}/{total} ({passed/total*100:.1f}%)**",
                ""
            ])

    # 总结
    lines.extend([
        "---",
        "",
        "## 总结",
        "",
        "| 类型 | 通过/总数 | 召回率 |",
        "|------|----------|--------|"
    ])

    for qtype, qname in [("factual", "事实型"), ("evidence", "证据集合型"), ("conflict", "冲突缺口型")]:
        stats = total_stats[qtype]
        rate = f"{stats['passed']/stats['total']*100:.1f}%" if stats['total'] > 0 else "-"
        lines.append(f"| {qname} | {stats['passed']}/{stats['total']} | {rate} |")

    total_passed = sum(s["passed"] for s in total_stats.values())
    total_all = sum(s["total"] for s in total_stats.values())
    total_rate = f"{total_passed/total_all*100:.1f}%" if total_all > 0 else "-"
    lines.extend([
        f"| **总计** | **{total_passed}/{total_all}** | **{total_rate}** |",
        ""
    ])

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n报告已保存到: {report_path}")


if __name__ == "__main__":
    run_benchmark_test()
