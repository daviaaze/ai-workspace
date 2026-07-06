"""Auction source parsers."""

from .base import BaseSource, SourceResult
from .leilao_net import LeilaoNet
from .receita_federal_sle import ReceitaFederalSLE

__all__ = [
    "BaseSource",
    "LeilaoNet",
    "ReceitaFederalSLE",
    "SourceResult",
]

