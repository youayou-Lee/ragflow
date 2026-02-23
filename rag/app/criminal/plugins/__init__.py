"""
Layer B plugins for document-type specific parsing.
"""

from .base import ParserPlugin
from .interrogation import InterrogationPlugin
from .indictment import IndictmentPlugin
from .scene_investigation import SceneInvestigationPlugin

__all__ = [
    "ParserPlugin",
    "InterrogationPlugin",
    "IndictmentPlugin",
    "SceneInvestigationPlugin",
]
