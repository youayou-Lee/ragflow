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
Lightweight NER for Layer A block extraction.

Extracts only amounts and dates to satisfy PRD constraints:
- "精确定位引用" (Precise citation)
- "禁止无证据断言" (No assertion without evidence)
"""

import re
from typing import Optional


def extract_lightweight_entities(text: str) -> Optional[dict]:
    """
    Extract amounts and dates from text.

    This is a lightweight NER that only extracts:
    - Amounts: numeric and Chinese numerals with currency units
    - Dates: ISO and Chinese date formats

    Args:
        text: Text content to extract entities from

    Returns:
        dict with "amounts" and "dates" lists, or None if no entities found
    """
    entities = {
        "amounts": [],
        "dates": []
    }

    # Amount patterns
    amount_patterns = [
        # Numeric with optional comma separators and decimals: 42000, 42,000.00
        r'(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*[元万]',
        # Chinese numerals with currency: 三万元, 一万
        r'([一二三四五六七八九十百千万亿]+)\s*[元万]',
    ]

    for pattern in amount_patterns:
        entities["amounts"].extend(re.findall(pattern, text))

    # Date patterns
    date_patterns = [
        # ISO format: 2024-01-15, 2024/03/20
        r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        # Chinese format: 2024年1月15日, 2024年3月
        r'(\d{4}年\d{1,2}月\d{1,2}日?)',
        # Partial date: 1月15日
        r'(\d{1,2}月\d{1,2}日)',
    ]

    for pattern in date_patterns:
        entities["dates"].extend(re.findall(pattern, text))

    # Deduplicate
    entities["amounts"] = list(set(entities["amounts"]))
    entities["dates"] = list(set(entities["dates"]))

    # Return None if no entities found
    if not entities["amounts"] and not entities["dates"]:
        return None

    return entities
