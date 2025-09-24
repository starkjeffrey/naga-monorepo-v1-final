"""Data Pipeline Core Module

Main pipeline orchestration and processing components.
"""

from .parsers import ClassIDParser, StudentNameParser
from .pipeline import PipelineOrchestrator
from .registry import PipelineRegistry, get_registry
from .stages import (
    Stage1Import,
    Stage2Profile,
    Stage3Clean,
    Stage4Validate,
    Stage5Transform,
    Stage6Split,
)

__all__ = [
    # Parsers
    "ClassIDParser",
    "StudentNameParser",
    # Pipeline
    "PipelineOrchestrator",
    # Registry
    "PipelineRegistry",
    "get_registry",
    # Stages
    "Stage1Import",
    "Stage2Profile",
    "Stage3Clean",
    "Stage4Validate",
    "Stage5Transform",
    "Stage6Split",
]
