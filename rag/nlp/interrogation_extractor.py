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
LLM-based metadata extraction for interrogation records.

This module provides functions to extract structured metadata from
interrogation record chunks using LLM.
"""

import json
import logging
import re
from typing import Optional

# Prompts for metadata extraction
HEADER_EXTRACTION_PROMPT = """你是法律文档分析助手。从以下讯问笔录头部信息中提取结构化数据：

{header_content}

请输出 JSON 格式（不要输出 markdown 代码块）：
{{
  "interrogation_time": "讯问时间",
  "location": "讯问地点",
  "interrogators": ["讯问人1", "讯问人2"],
  "recorder": "记录人",
  "suspect_name": "被讯问人姓名",
  "suspect_gender": "性别",
  "suspect_birth": "出生日期",
  "suspect_id": "身份证号",
  "suspect_address": "户籍地址",
  "case_type": "案件类型（如诈骗、盗窃等）"
}}

如果某字段无法提取，设为 null。只输出 JSON，不要其他文字。"""

QA_EXTRACTION_PROMPT = """你是法律文档分析助手。从以下讯问笔录问答中提取实体和标签：

问：{question}
答：{answer}

请输出 JSON 格式（不要输出 markdown 代码块）：
{{
  "entities": {{
    "persons": ["提到的人名"],
    "orgs": ["机构名称"],
    "locations": ["地点"],
    "dates": ["日期，标准化为 YYYY-MM-DD 格式"],
    "amounts": [金额数值，如 42000],
    "phones": ["电话号码"],
    "id_numbers": ["身份证/证件号"]
  }},
  "tags": ["内容标签，如：收款、退款、转账、认罪、否认、辩解"],
  "topic": "主题分类：程序性/身份核验/案件事实/人物关系/辩解陈述",
  "key_facts": ["关键事实摘要，最多3条"]
}}

只输出 JSON，不要其他文字。"""

QA_SEGMENTATION_PROMPT = """你是一个法律文档分析助手。以下是讯问笔录中的一段问答：

问：{question}

答：{answer}

这段回答较长，请按语义将其分成 2-4 个自然段落。
输出 JSON 格式（不要输出 markdown 代码块）：
{{
  "segments": [
    {{"content": "第一段内容", "summary": "简短摘要(10字内)"}},
    {{"content": "第二段内容", "summary": "简短摘要(10字内)"}}
  ]
}}

只输出 JSON，不要其他文字。"""

ORDER_INFERENCE_PROMPT = """你是法律案件分析助手。基于以下问答内容，推断其中描述事件的相对时间顺序：

问答序号 {qa_index}：
问：{question}
答：{answer}

已知此问答在笔录中的位置是第 {qa_index} 个问答。
请推断这段回答中描述的主要事件在整个案件时间线中的相对位置。

输出 JSON 格式（不要输出 markdown 代码块）：
{{
  "mentioned_events": [
    {{
      "event": "事件简述",
      "has_explicit_date": true,
      "inferred_order": "before_qa_X 或 after_qa_Y 或 around_qa_Z 或 same_as_qa"
    }}
  ]
}}

注意：仅基于内容中的时间词（如"之后"、"之前"、"当天"等）推断，不要臆测。
只输出 JSON，不要其他文字。"""


def parse_llm_json_response(response: str) -> Optional[dict]:
    """
    Parse JSON from LLM response, handling various formats.

    Args:
        response: Raw LLM response text

    Returns:
        dict or None: Parsed JSON or None if parsing failed
    """
    if not response:
        return None

    # Remove markdown code blocks if present
    response = response.strip()
    if response.startswith("```"):
        # Remove opening ```json or ```
        lines = response.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        response = "\n".join(lines)

    # Try to find JSON in the response
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # Try to extract JSON using regex
        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

    logging.warning(f"Failed to parse LLM response as JSON: {response[:200]}...")
    return None


def extract_header_metadata(llm_client, header_content: str) -> Optional[dict]:
    """
    Extract metadata from header section using LLM.

    Args:
        llm_client: LLM client instance
        header_content: Header text content

    Returns:
        dict or None: Extracted metadata
    """
    if not header_content or not llm_client:
        return None

    try:
        prompt = HEADER_EXTRACTION_PROMPT.format(header_content=header_content)
        response = llm_client.chat(prompt, gen_conf={"temperature": 0.1})
        return parse_llm_json_response(response)
    except Exception as e:
        logging.error(f"Error extracting header metadata: {e}")
        return None


def extract_qa_metadata(llm_client, question: str, answer: str) -> Optional[dict]:
    """
    Extract metadata from QA pair using LLM.

    Args:
        llm_client: LLM client instance
        question: Question text
        answer: Answer text

    Returns:
        dict or None: Extracted metadata
    """
    if not llm_client:
        return None

    try:
        prompt = QA_EXTRACTION_PROMPT.format(question=question, answer=answer)
        response = llm_client.chat(prompt, gen_conf={"temperature": 0.1})
        return parse_llm_json_response(response)
    except Exception as e:
        logging.error(f"Error extracting QA metadata: {e}")
        return None


def segment_long_answer(llm_client, question: str, answer: str) -> Optional[list]:
    """
    Segment a long answer into semantic parts using LLM.

    Args:
        llm_client: LLM client instance
        question: Question text
        answer: Answer text (should be long)

    Returns:
        list or None: List of segment dicts with 'content' and 'summary' keys
    """
    if not llm_client:
        return None

    try:
        prompt = QA_SEGMENTATION_PROMPT.format(question=question, answer=answer)
        response = llm_client.chat(prompt, gen_conf={"temperature": 0.1})
        result = parse_llm_json_response(response)
        if result and "segments" in result:
            return result["segments"]
        return None
    except Exception as e:
        logging.error(f"Error segmenting long answer: {e}")
        return None


def infer_event_order(llm_client, question: str, answer: str, qa_index: int) -> Optional[dict]:
    """
    Infer the temporal order of events mentioned in a QA pair.

    Args:
        llm_client: LLM client instance
        question: Question text
        answer: Answer text
        qa_index: Index of this QA pair in the document

    Returns:
        dict or None: Order inference result
    """
    if not llm_client:
        return None

    try:
        prompt = ORDER_INFERENCE_PROMPT.format(question=question, answer=answer, qa_index=qa_index)
        response = llm_client.chat(prompt, gen_conf={"temperature": 0.1})
        return parse_llm_json_response(response)
    except Exception as e:
        logging.error(f"Error inferring event order: {e}")
        return None


def enhance_chunk_with_metadata(chunk: dict, llm_client) -> dict:
    """
    Enhance a chunk with LLM-extracted metadata.

    Args:
        chunk: Chunk dictionary
        llm_client: LLM client instance

    Returns:
        dict: Enhanced chunk with metadata field
    """
    chunk_type = chunk.get("chunk_type")
    content = chunk.get("content_with_weight", "")

    if not content or not llm_client:
        return chunk

    metadata = None

    if chunk_type == "header":
        metadata = extract_header_metadata(llm_client, content)
    elif chunk_type == "qa_pair":
        # Parse question and answer from content
        parts = content.split("\t", 1)
        question = parts[0] if parts else ""
        answer = parts[1] if len(parts) > 1 else ""
        metadata = extract_qa_metadata(llm_client, question, answer)

        # Also try to infer event order
        qa_index = chunk.get("qa_index", 0)
        order_info = infer_event_order(llm_client, question, answer, qa_index)
        if order_info:
            if metadata:
                metadata["order_info"] = order_info
            else:
                metadata = {"order_info": order_info}

    if metadata:
        chunk["metadata"] = metadata

    return chunk
