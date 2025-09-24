"""Class part type definitions for the scheduling system.

Centralized definitions for class component types used by both
ClassPart and ClassPartTemplate models.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class ClassPartType(models.TextChoices):
    """Types of class components used in scheduling.

    Used by both language programs (multiple parts per class) and
    academic programs (typically single part per class).
    """

    # General Academic Types
    MAIN = "MAIN", _("Main Class")
    LECTURE = "LECTURE", _("Lecture")
    DISCUSSION = "DISCUSSION", _("Discussion")
    LAB = "LAB", _("Laboratory")
    COMPUTER = "COMPUTER", _("Computer Lab")
    WORKSHOP = "WORKSHOP", _("Workshop")
    TUTORIAL = "TUTORIAL", _("Tutorial")
    PROJECT = "PROJECT", _("Project")

    # Language-Specific Types
    GRAMMAR = "GRAMMAR", _("Grammar")
    CONVERSATION = "CONVERSATION", _("Conversation")
    WRITING = "WRITING", _("Writing")
    READING = "READING", _("Reading")
    LISTENING = "LISTENING", _("Listening")
    SPEAKING = "SPEAKING", _("Speaking")

    # Textbook-Based (for clerk convenience)
    VENTURES = "VENTURES", _("Ventures")  # Ventures textbook

    # Academic Program-Specific
    BA = "BA", _("Bachelor's Degree")  # BA program courses
    MA = "MA", _("Master's Degree")  # MA program courses
    PRACTICUM = "PRACTICUM", _("Practicum")  # Practical experience
    EXCHANGE = "EXCHANGE", _("Exchange Program")  # Exchange programs

    # Delivery Methods
    ONLINE = "ONLINE", _("Online Class")

    # Other
    OTHER = "OTHER", _("Other")
