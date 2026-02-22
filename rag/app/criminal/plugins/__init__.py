"""
Layer B plugins for document-type specific parsing.
"""

from .base import ParserPlugin
from .interrogation import InterrogationPlugin

__all__ = ["ParserPlugin", "InterrogationPlugin"]
