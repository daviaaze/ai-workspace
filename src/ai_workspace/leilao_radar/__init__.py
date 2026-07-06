"""Leilão Radar — Automated auction opportunity scanner for Brazilian government auctions."""

from ai_workspace.leilao_radar.config import Config
from ai_workspace.leilao_radar.sources import BaseSource, LeilaoNet, ReceitaFederalSLE

__all__ = [
    "Config",
    "BaseSource",
    "LeilaoNet",
    "ReceitaFederalSLE",
]

