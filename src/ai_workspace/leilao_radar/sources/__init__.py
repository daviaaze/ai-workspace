"""Auction source parsers."""

from .base import BaseSource, SourceResult
from .leilao_net import LeilaoNet
from .receita_federal_sle import ReceitaFederalSLE
from .caixa_imoveis import CaixaImoveis
from .bb_leiloes import BancoDoBrasilLeiloes
from .pf_leiloes import PoliciaFederalLeiloes
from .prf_leiloes import PRFLeiloes
from .leiloes_judiciais import LeiloesJudiciais
from .sefaz_leiloes import SefazLeiloes

__all__ = [
    "BaseSource",
    "SourceResult",
    "LeilaoNet",
    "ReceitaFederalSLE",
    "CaixaImoveis",
    "BancoDoBrasilLeiloes",
    "PoliciaFederalLeiloes",
    "PRFLeiloes",
    "LeiloesJudiciais",
    "SefazLeiloes",
]

