#!/usr/bin/env python3

# PEP 723 metadata
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "nltk",
#   "huggingface-hub"
# ]
# ///

import argparse
import os
import socket
import urllib.request
import zipfile
from contextlib import contextmanager
from typing import Union

import nltk
from huggingface_hub import snapshot_download


def get_urls(use_china_mirrors=False) -> list[Union[str, list[str]]]:
    if use_china_mirrors:
        return [
            "http://mirrors.tuna.tsinghua.edu.cn/ubuntu/pool/main/o/openssl/libssl1.1_1.1.1f-1ubuntu2_amd64.deb",
            "http://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports/pool/main/o/openssl/libssl1.1_1.1.1f-1ubuntu2_arm64.deb",
            "https://repo.huaweicloud.com/repository/maven/org/apache/tika/tika-server-standard/3.2.3/tika-server-standard-3.2.3.jar",
            "https://repo.huaweicloud.com/repository/maven/org/apache/tika/tika-server-standard/3.2.3/tika-server-standard-3.2.3.jar.md5",
            "https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken",
            ["https://registry.npmmirror.com/-/binary/chrome-for-testing/121.0.6167.85/linux64/chrome-linux64.zip", "chrome-linux64-121-0-6167-85"],
            ["https://registry.npmmirror.com/-/binary/chrome-for-testing/121.0.6167.85/linux64/chromedriver-linux64.zip", "chromedriver-linux64-121-0-6167-85"],
            "https://github.com/astral-sh/uv/releases/download/0.9.16/uv-x86_64-unknown-linux-gnu.tar.gz",
            "https://github.com/astral-sh/uv/releases/download/0.9.16/uv-aarch64-unknown-linux-gnu.tar.gz",
        ]
    else:
        return [
            "http://archive.ubuntu.com/ubuntu/pool/main/o/openssl/libssl1.1_1.1.1f-1ubuntu2_amd64.deb",
            "http://ports.ubuntu.com/pool/main/o/openssl/libssl1.1_1.1.1f-1ubuntu2_arm64.deb",
            "https://repo1.maven.org/maven2/org/apache/tika/tika-server-standard/3.2.3/tika-server-standard-3.2.3.jar",
            "https://repo1.maven.org/maven2/org/apache/tika/tika-server-standard/3.2.3/tika-server-standard-3.2.3.jar.md5",
            "https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken",
            ["https://storage.googleapis.com/chrome-for-testing-public/121.0.6167.85/linux64/chrome-linux64.zip", "chrome-linux64-121-0-6167-85"],
            ["https://storage.googleapis.com/chrome-for-testing-public/121.0.6167.85/linux64/chromedriver-linux64.zip", "chromedriver-linux64-121-0-6167-85"],
            "https://github.com/astral-sh/uv/releases/download/0.9.16/uv-x86_64-unknown-linux-gnu.tar.gz",
            "https://github.com/astral-sh/uv/releases/download/0.9.16/uv-aarch64-unknown-linux-gnu.tar.gz",
        ]


repos = [
    "InfiniFlow/text_concat_xgb_v1.0",
    "InfiniFlow/deepdoc",
]


# 设置全局超时
@contextmanager
def set_timeout(timeout):
    """设置全局 socket 超时"""
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try:
        yield
    finally:
        socket.setdefaulttimeout(old_timeout)


def download_url_with_timeout(url, dest, timeout=30):
    """带超时的 URL 下载"""
    with set_timeout(timeout):
        urllib.request.urlretrieve(url, dest)


def download_model(repository_id):
    local_directory = os.path.abspath(os.path.join("huggingface.co", repository_id))
    os.makedirs(local_directory, exist_ok=True)
    snapshot_download(repo_id=repository_id, local_dir=local_directory)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download dependencies with optional China mirror support")
    parser.add_argument("--china-mirrors", action="store_true", help="Use China-accessible mirrors for downloads")
    args = parser.parse_args()

    urls = get_urls(args.china_mirrors)

    for url in urls:
        download_url = url[0] if isinstance(url, list) else url
        filename = url[1] if isinstance(url, list) else url.split("/")[-1]
        print(f"Downloading {filename} from {download_url}...")
        if not os.path.exists(filename):
            urllib.request.urlretrieve(download_url, filename)

    local_dir = os.path.abspath("nltk_data")
    nltk_data_dir = os.path.join(local_dir, "nltk_data")

    # NLTK 下载函数（支持国内镜像）
    def download_nltk_data():
        """下载 NLTK 数据，使用国内镜像"""
        # 定义 NLTK 数据包及其对应的下载链接
        # 使用多个备用源
        nltk_packages = []

        if args.china_mirrors:
            # 尝试多个镜像源
            sources = [
                # 清华大学开源镜像
                {
                    "punkt": "https://mirrors.tuna.tsinghua.edu.cn/nltk_data/packages/tokenizers/punkt.zip",
                    "punkt_tab": "https://mirrors.tuna.tsinghua.edu.cn/nltk_data/packages/tokenizers/punkt_tab.zip",
                    "wordnet": "https://mirrors.tuna.tsinghua.edu.cn/nltk_data/packages/corpora/wordnet.zip",
                },
                # 使用 gitclone 镜像
                {
                    "punkt": "https://gitclone.com/github.com/nltk/nltk_data/raw/gh-pages/packages/tokenizers/punkt.zip",
                    "punkt_tab": "https://gitclone.com/github.com/nltk/nltk_data/raw/gh-pages/packages/tokenizers/punkt_tab.zip",
                    "wordnet": "https://gitclone.com/github.com/nltk/nltk_data/raw/gh-pages/packages/corpora/wordnet.zip",
                },
            ]
            nltk_packages = sources
        else:
            # 原始 GitHub 源
            nltk_packages = [{
                "punkt": "https://github.com/nltk/nltk_data/raw/gh-pages/packages/tokenizers/punkt.zip",
                "punkt_tab": "https://github.com/nltk/nltk_data/raw/gh-pages/packages/tokenizers/punkt_tab.zip",
                "wordnet": "https://github.com/nltk/nltk_data/raw/gh-pages/packages/corpora/wordnet.zip",
            }]

        # 尝试从每个源下载
        for source_idx, source_urls in enumerate(nltk_packages):
            success_count = 0
            for data_name, url in source_urls.items():
                print(f"Downloading nltk {data_name}... (source {source_idx + 1})")
                zip_path = os.path.join(local_dir, f"{data_name}.zip")

                # 检查是否已经下载并解压
                extracted_path = os.path.join(nltk_data_dir, "tokenizers" if data_name.startswith("punkt") else "corpora")
                if os.path.exists(extracted_path):
                    target_file = os.path.join(extracted_path, data_name if data_name.startswith("punkt") else data_name)
                    if os.path.exists(target_file):
                        print(f"  {data_name} already exists, skipping...")
                        success_count += 1
                        continue

                try:
                    # 下载 zip 文件
                    if not os.path.exists(zip_path):
                        download_url_with_timeout(url, zip_path, timeout=30)

                    # 解压到 nltk_data 目录
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(nltk_data_dir)

                    print(f"  Successfully downloaded and extracted {data_name}")
                    success_count += 1

                except Exception as e:
                    print(f"  Failed to download {data_name}: {e}")
                    # 继续尝试下一个包
                finally:
                    # 清理 zip 文件
                    if os.path.exists(zip_path):
                        os.remove(zip_path)

            # 如果这个源成功下载了所有包，就退出
            if success_count == 3:
                print(f"All NLTK data downloaded successfully from source {source_idx + 1}")
                return

        print("Warning: Some NLTK data packages failed to download. You may need to download them manually.")

    download_nltk_data()

    for repo_id in repos:
        print(f"Downloading huggingface repo {repo_id}...")
        download_model(repo_id)
