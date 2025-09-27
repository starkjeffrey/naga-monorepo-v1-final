"""GraphQL mutation resolvers for the Naga SIS system."""

from .grades import GradeMutations
from .finance import FinanceMutations

__all__ = [
    "GradeMutations",
    "FinanceMutations",
]