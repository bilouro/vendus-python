"""Tax models and AT exemption codes."""

from __future__ import annotations

from enum import Enum


class TaxExemption(str, Enum):
    """AT-mandated VAT exemption reason codes (M01-M99).

    Use when a line item has tax_rate == 0 and an exemption reason is required.
    Full list is published by Autoridade Tributária. The codes here are the most
    common; add to this enum as needed.
    """

    M01 = "M01"  # Artigo 16.º, n.º 6 do CIVA
    M02 = "M02"  # Artigo 6.º do Decreto-Lei n.º 198/90
    M04 = "M04"  # Isento Artigo 13.º do CIVA
    M05 = "M05"  # Isento Artigo 14.º do CIVA
    M06 = "M06"  # Isento Artigo 15.º do CIVA
    M07 = "M07"  # Isento Artigo 9.º do CIVA
    M09 = "M09"  # IVA - não confere direito a dedução
    M10 = "M10"  # IVA - Regime de IVA de caixa
    M11 = "M11"  # Regime particular do tabaco
    M12 = "M12"  # Regime da margem de lucro - Agências de viagens
    M13 = "M13"  # Regime da margem de lucro - Bens em segunda mão
    M14 = "M14"  # Regime da margem de lucro - Objetos de arte
    M15 = "M15"  # Regime da margem de lucro - Objetos de coleção e antiguidades
    M16 = "M16"  # Isento Artigo 14.º do RITI
    M19 = "M19"  # Outras isenções
    M20 = "M20"  # IVA - regime forfetário
    M21 = "M21"  # IVA - não confere direito à dedução
    M25 = "M25"  # Mercadorias à consignação
    M99 = "M99"  # Não sujeito; não tributado
