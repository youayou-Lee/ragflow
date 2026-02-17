#!/usr/bin/env python3
"""
PR-6 端到端测试脚本
测试 PaddleVL 作为默认 PDF 解析器

使用方法:
  uv run python test_pr6_e2e.py

前提条件:
  1. RAGFlow 服务正在运行 (http://localhost:9380)
  2. Docker 依赖服务运行中 (MySQL, ES, MinIO)
"""

import os
import sys
import time
import requests
from pathlib import Path

# 加载环境变量
_env_test_path = Path(__file__).parent / ".env.test"
if _env_test_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_test_path)

# 配置
BASE_URL = os.getenv("HOST_ADDRESS", "http://127.0.0.1:9380")
VERSION = "v1"  # 用户认证 API
SDK_URL = f"{BASE_URL}/api/v1"  # SDK API
PDF_PATH = os.getenv("PDF_PATH", "/home/you/cs/proj/Superyou/SampleData/讯问笔录_sample.pdf")

# 测试用户配置 (与 test/testcases/configs.py 保持一致)
EMAIL = "qa@infiniflow.org"
# password is "123"
PASSWORD = """ctAseGvejiaSWWZ88T/m4FQVOpQyUvP+x7sXtdv3feqZACiQleuewkUi35E16wSd5C5QcnkkcV9cYc8TKPTRZlxappDuirxghxoOvFcJxFU4ixLsD
fN33jCHRoDUW81IH9zjij/vaw8IbVyb6vuwg6MX6inOEBRRzVbRYxXOu1wkWY6SsI8X70oF9aeLFp/PzQpjoe/YbSqpTq8qqrmHzn9vO+yvyYyvmDsphXe
X8f7fp9c7vUsfOCkM+gHY3PadG+QHa7KI7mzTKgUTZImK6BZtfRBATDTthEUbbaTewY4H0MnWiCeeDhcbeQao6cFy1To8pE3RpmxnGnS8BsBn8w=="""


def register():
    """注册测试用户"""
    url = f"{BASE_URL}/{VERSION}/user/register"
    register_data = {"email": EMAIL, "nickname": "qa", "password": PASSWORD}
    res = requests.post(url=url, json=register_data)
    res_json = res.json()
    if res_json.get("code") != 0 and "has already registered" not in res_json.get("message", ""):
        raise Exception(res_json.get("message"))
    print(f"✓ 用户注册完成: {EMAIL}")


def login():
    """登录并返回 Authorization header"""
    url = f"{BASE_URL}/{VERSION}/user/login"
    login_data = {"email": EMAIL, "password": PASSWORD}
    response = requests.post(url=url, json=login_data)
    res = response.json()
    if res.get("code") != 0:
        raise Exception(res.get("message"))
    auth = response.headers["Authorization"]
    return auth


def get_token(auth):
    """获取 API token"""
    url = f"{BASE_URL}/{VERSION}/system/new_token"
    headers = {"Authorization": auth}
    response = requests.post(url=url, headers=headers)
    res = response.json()
    if res.get("code") != 0:
        raise Exception(res.get("message"))
    return res["data"].get("token")


def create_dataset(token, name):
    """创建数据集"""
    url = f"{SDK_URL}/datasets"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(url=url, headers=headers, json={"name": name})

    if resp.status_code == 200:
        data = resp.json()
        if data.get("code") == 0:
            dataset = data["data"]
            print(f"✓ 创建数据集: {name} (ID: {dataset['id']})")
            return dataset

    print(f"✗ 创建数据集失败: {resp.text}")
    return None


def get_dataset_config(token, dataset_id):
    """获取数据集配置，验证默认解析器"""
    # 获取数据集列表
    url = f"{SDK_URL}/datasets"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url=url, headers=headers)

    if resp.status_code == 200:
        data = resp.json()
        if data.get("code") == 0:
            # 从列表中找到对应的数据集
            for ds in data["data"]:
                if ds["id"] == dataset_id:
                    return ds

    return None


def upload_document(token, dataset_id, pdf_path):
    """上传文档"""
    if not os.path.exists(pdf_path):
        print(f"✗ 文件不存在: {pdf_path}")
        return None

    url = f"{SDK_URL}/datasets/{dataset_id}/documents"
    headers = {"Authorization": f"Bearer {token}"}

    with open(pdf_path, "rb") as f:
        resp = requests.post(
            url=url,
            headers=headers,
            files={"file": (Path(pdf_path).name, f, "application/pdf")}
        )

    if resp.status_code == 200:
        data = resp.json()
        if data.get("code") == 0:
            docs = data["data"]
            if docs:
                doc = docs[0]
                print(f"✓ 上传文档: {doc['name']} (ID: {doc['id']})")
                return doc

    print(f"✗ 上传文档失败: {resp.text}")
    return None


def run_document_parser(token, dataset_id, document_id):
    """运行文档解析"""
    url = f"{SDK_URL}/datasets/{dataset_id}/chunks"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(url=url, headers=headers, json={"document_ids": [document_id]})

    if resp.status_code == 200:
        data = resp.json()
        if data.get("code") == 0:
            print(f"✓ 启动解析任务")
            return True

    print(f"✗ 启动解析失败: {resp.text}")
    return False


def check_document_status(token, dataset_id, document_id, timeout=180):
    """检查文档解析状态"""
    url = f"{SDK_URL}/datasets/{dataset_id}/documents"
    headers = {"Authorization": f"Bearer {token}"}
    start_time = time.time()

    while time.time() - start_time < timeout:
        resp = requests.get(url=url, headers=headers)

        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == 0:
                # 文档列表在 data.docs 中
                docs = data["data"].get("docs", [])
                for doc in docs:
                    if doc["id"] == document_id:
                        status = doc.get("status", "unknown")
                        run_status = doc.get("run", "UNSTART")
                        chunk_count = doc.get("chunk_count", 0)

                        print(f"  解析状态: {run_status}, 文档状态: {status}, chunks: {chunk_count}")

                        if run_status == "DONE" and chunk_count > 0:
                            print(f"✓ 解析完成! Chunk 数量: {chunk_count}")
                            return doc
                        elif run_status == "FAIL":
                            print(f"✗ 解析失败")
                            return None
                        break

        time.sleep(3)

    print(f"✗ 解析超时")
    return None


def main():
    print("=" * 50)
    print("PR-6 端到端测试: PaddleVL 默认解析器")
    print("=" * 50)
    print()

    # 1. 认证
    print("[1/7] 用户认证...")
    try:
        register()
    except Exception as e:
        print(f"  (注册跳过: {e})")

    try:
        auth = login()
        print(f"✓ 登录成功: {EMAIL}")
    except Exception as e:
        print(f"✗ 登录失败: {e}")
        sys.exit(1)

    # 获取 API Token
    try:
        token = get_token(auth)
        print(f"✓ 获取 API Token 成功")
    except Exception as e:
        print(f"✗ 获取 Token 失败: {e}")
        sys.exit(1)

    # 2. 创建数据集
    print()
    print("[2/7] 创建测试数据集...")
    dataset_name = f"pr6_test_{int(time.time())}"
    dataset = create_dataset(token, dataset_name)
    if not dataset:
        sys.exit(1)

    # 3. 验证默认配置
    print()
    print("[3/7] 验证默认解析器配置...")
    config = get_dataset_config(token, dataset["id"])
    if config:
        parser_config = config.get("parser_config", {})
        layout_recognize = parser_config.get("layout_recognize", "")
        print(f"  layout_recognize: {layout_recognize}")

        if layout_recognize == "PaddleOCR-VL@paddleocr":
            print("✓ 默认解析器配置正确!")
        else:
            print(f"✗ 默认解析器配置错误，期望 PaddleOCR-VL@paddleocr，实际 {layout_recognize}")
            sys.exit(1)
    else:
        print("✗ 无法获取数据集配置")
        sys.exit(1)

    # 4. 上传文档
    print()
    print("[4/7] 上传测试文档...")
    document = upload_document(token, dataset["id"], PDF_PATH)
    if not document:
        sys.exit(1)

    # 5. 运行解析
    print()
    print("[5/7] 启动 PDF 解析...")
    if not run_document_parser(token, dataset["id"], document["id"]):
        sys.exit(1)

    # 6. 等待解析完成
    print()
    print("[6/7] 等待解析完成...")
    result = check_document_status(token, dataset["id"], document["id"])

    # 7. 验证结果
    print()
    print("[7/7] 验证解析结果...")
    if result:
        chunk_count = result.get("chunk_count", 0)
        if chunk_count > 0:
            print(f"✓ 解析成功，生成 {chunk_count} 个 chunks")
        else:
            print("✗ 解析完成但没有生成 chunks")
            sys.exit(1)

    print()
    print("=" * 50)
    if result and result.get("chunk_count", 0) > 0:
        print("✓ PR-6 端到端测试通过!")
        print("  - PaddleVL 作为默认解析器工作正常")
        print("  - PDF 解析成功")
        print("  - layout_recognize = PaddleOCR-VL@paddleocr")
    else:
        print("✗ PR-6 端到端测试失败")
        sys.exit(1)
    print("=" * 50)


if __name__ == "__main__":
    main()
