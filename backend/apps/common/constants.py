"""Constants and enums for the Naga SIS project.

This module contains shared constants, enums, and choices that are used
across multiple apps in the system. This follows clean architecture
principles by centralizing common data definitions.

Key principles:
- Static data that doesn't change frequently
- Reference data used across multiple apps
- Avoids creating unnecessary database models for simple enums
"""

from django.utils.translation import gettext_lazy as _


class CambodianProvinces:
    """Cambodian provinces and special administrative areas.

    This enum contains all 25 provinces/municipalities in Cambodia.
    The codes use standardized naming for consistency across the system.
    """

    # Provinces (alphabetical order by English name)
    BANTEAY_MEANCHEY = "BANTEAY_MEANCHEY"
    BATTAMBANG = "BATTAMBANG"
    KAMPONG_CHAM = "KAMPONG_CHAM"
    KAMPONG_CHHNANG = "KAMPONG_CHHNANG"
    KAMPONG_SPEU = "KAMPONG_SPEU"
    KAMPONG_THOM = "KAMPONG_THOM"
    KAMPOT = "KAMPOT"
    KANDAL = "KANDAL"
    KEP = "KEP"
    KOH_KONG = "KOH_KONG"
    KRATIE = "KRATIE"
    MONDULKIRI = "MONDULKIRI"
    ODDAR_MEANCHEY = "ODDAR_MEANCHEY"
    PAILIN = "PAILIN"
    PHNOM_PENH = "PHNOM_PENH"
    PREAH_SIHANOUK = "PREAH_SIHANOUK"
    PREAH_VIHEAR = "PREAH_VIHEAR"
    PREY_VENG = "PREY_VENG"
    PURSAT = "PURSAT"
    RATANAKIRI = "RATANAKIRI"
    SIEM_REAP = "SIEM_REAP"
    STUNG_TRENG = "STUNG_TRENG"
    SVAY_RIENG = "SVAY_RIENG"
    TAKEO = "TAKEO"
    TBOUNG_KHMUM = "TBOUNG_KHMUM"

    # Special case for international/unknown
    INTERNATIONAL = "INTERNATIONAL"
    UNKNOWN = "UNKNOWN"


# Django choices for forms and models
CAMBODIAN_PROVINCE_CHOICES = [
    (CambodianProvinces.BANTEAY_MEANCHEY, _("Banteay Meanchey")),
    (CambodianProvinces.BATTAMBANG, _("Battambang")),
    (CambodianProvinces.KAMPONG_CHAM, _("Kampong Cham")),
    (CambodianProvinces.KAMPONG_CHHNANG, _("Kampong Chhnang")),
    (CambodianProvinces.KAMPONG_SPEU, _("Kampong Speu")),
    (CambodianProvinces.KAMPONG_THOM, _("Kampong Thom")),
    (CambodianProvinces.KAMPOT, _("Kampot")),
    (CambodianProvinces.KANDAL, _("Kandal")),
    (CambodianProvinces.KEP, _("Kep")),
    (CambodianProvinces.KOH_KONG, _("Koh Kong")),
    (CambodianProvinces.KRATIE, _("Kratie")),
    (CambodianProvinces.MONDULKIRI, _("Mondulkiri")),
    (CambodianProvinces.ODDAR_MEANCHEY, _("Oddar Meanchey")),
    (CambodianProvinces.PAILIN, _("Pailin")),
    (CambodianProvinces.PHNOM_PENH, _("Phnom Penh")),
    (CambodianProvinces.PREAH_SIHANOUK, _("Preah Sihanouk")),
    (CambodianProvinces.PREAH_VIHEAR, _("Preah Vihear")),
    (CambodianProvinces.PREY_VENG, _("Prey Veng")),
    (CambodianProvinces.PURSAT, _("Pursat")),
    (CambodianProvinces.RATANAKIRI, _("Ratanakiri")),
    (CambodianProvinces.SIEM_REAP, _("Siem Reap")),
    (CambodianProvinces.STUNG_TRENG, _("Stung Treng")),
    (CambodianProvinces.SVAY_RIENG, _("Svay Rieng")),
    (CambodianProvinces.TAKEO, _("Takeo")),
    (CambodianProvinces.TBOUNG_KHMUM, _("Tboung Khmum")),
    (CambodianProvinces.INTERNATIONAL, _("International/Other")),
    (CambodianProvinces.UNKNOWN, _("Unknown")),
]

# Alias for birth place choices (same as provinces for now)
BIRTH_PLACE_CHOICES = CAMBODIAN_PROVINCE_CHOICES


def get_province_display_name(province_code: str) -> str:
    """Get the display name for a province code.

    Args:
        province_code: The province code constant

    Returns:
        The translated display name for the province
    """
    province_dict = dict(CAMBODIAN_PROVINCE_CHOICES)
    return str(province_dict.get(province_code, province_code))


def is_cambodian_province(province_code: str) -> bool:
    """Check if a province code represents a Cambodian province.

    Args:
        province_code: The province code to check

    Returns:
        True if it's a Cambodian province, False if international/other
    """
    return province_code != CambodianProvinces.INTERNATIONAL


class Buildings:
    """Campus buildings where classes and activities take place.

    These are the fixed buildings on campus that house classrooms
    and other facilities.
    """

    MAIN = "MAIN"
    WEST = "WEST"
    BACK = "BACK"


# Django choices for building selection
BUILDING_CHOICES = [
    (Buildings.MAIN, _("Main Building")),
    (Buildings.WEST, _("West Building")),
    (Buildings.BACK, _("Back Building")),
]


def get_building_display_name(building_code: str) -> str:
    """Get the display name for a building code.

    Args:
        building_code: The building code constant

    Returns:
        The translated display name for the building
    """
    building_dict = dict(BUILDING_CHOICES)
    return str(building_dict.get(building_code, building_code))
