"""
Criminal document parsing module.

Architecture:
- Layer A: Universal Block extraction (blocks.py, ner.py)
- Layer B: Document-type specific plugins (plugins/)
"""

from .blocks import UniversalBlock, BlockType

__all__ = ["UniversalBlock", "BlockType"]
