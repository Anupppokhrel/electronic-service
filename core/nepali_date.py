"""
Bikram Sambat (BS) <-> Gregorian (AD) Date Converter and Formatter for Nepal.
Lightweight, accurate lookup-table based converter supporting 2075 BS - 2090 BS (2018 AD - 2034 AD).
"""
from datetime import date, datetime

# Days in each month for Bikram Sambat years 2075 to 2090 (Baishakh to Chaitra)
# Each tuple has 12 integers representing days in [Baisakh, Jestha, Ashadh, Shrawan, Bhadra, Ashwin, Kartik, Mangsir, Poush, Magh, Falgun, Chaitra]
BS_CALENDAR_DATA = {
    2075: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2076: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30),
    2077: (31, 32, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30),
    2078: (31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30),
    2079: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2080: (31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30),
    2081: (31, 31, 32, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2082: (31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 30, 30),
    2083: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2084: (31, 31, 32, 31, 32, 30, 30, 30, 29, 30, 29, 31),
    2085: (31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2086: (31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 30, 30),
    2087: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30),
    2088: (31, 31, 32, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2089: (31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31),
    2090: (31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 30, 30),
}

# Anchor date: 2075-01-01 BS = 2018-04-14 AD
ANCHOR_BS_YEAR = 2075
ANCHOR_AD_DATE = date(2018, 4, 14)

NEPALI_MONTH_NAMES_EN = [
    "Baisakh", "Jestha", "Ashadh", "Shrawan", "Bhadra", "Ashwin",
    "Kartik", "Mangsir", "Poush", "Magh", "Falgun", "Chaitra"
]

NEPALI_MONTH_NAMES_NP = [
    "वैशाख", "जेठ", "असार", "साउन", "भदौ", "असोज",
    "कात्तिक", "मंसिर", "पुस", "माघ", "फागुन", "चैत"
]

def ad_to_bs(ad_input):
    """
    Converts a Python datetime or date object to (bs_year, bs_month, bs_day).
    """
    if ad_input is None:
        return None
    if isinstance(ad_input, datetime):
        ad_input = ad_input.date()

    delta_days = (ad_input - ANCHOR_AD_DATE).days
    if delta_days < 0:
        # Fallback approximation for dates earlier than anchor
        return (ad_input.year + 56, ad_input.month, ad_input.day)

    current_bs_year = ANCHOR_BS_YEAR
    while current_bs_year in BS_CALENDAR_DATA:
        year_days = sum(BS_CALENDAR_DATA[current_bs_year])
        if delta_days < year_days:
            break
        delta_days -= year_days
        current_bs_year += 1

    if current_bs_year not in BS_CALENDAR_DATA:
        return (ad_input.year + 57, ad_input.month, ad_input.day)

    months_days = BS_CALENDAR_DATA[current_bs_year]
    current_bs_month = 1
    for m_days in months_days:
        if delta_days < m_days:
            break
        delta_days -= m_days
        current_bs_month += 1

    current_bs_day = delta_days + 1
    return (current_bs_year, current_bs_month, current_bs_day)

def format_bs_date(ad_input, format_style="standard"):
    """
    Returns formatted Bikram Sambat date string.
    - standard: "8 Ashwin 2083 BS"
    - short: "8/6/2083 BS"
    - full: "24 Sep 2026 / 8 Ashwin 2083 BS"
    """
    if not ad_input:
        return ""
    
    bs_tuple = ad_to_bs(ad_input)
    if not bs_tuple:
        return ""
    
    bs_year, bs_month, bs_day = bs_tuple
    month_name = NEPALI_MONTH_NAMES_EN[bs_month - 1]

    if format_style == "short":
        return f"{bs_day}/{bs_month}/{bs_year} BS"
    elif format_style == "numeric":
        return f"{bs_year}-{bs_month:02d}-{bs_day:02d}"
    elif format_style == "full":
        if isinstance(ad_input, datetime):
            ad_str = ad_input.strftime("%d %b %Y")
        else:
            ad_str = ad_input.strftime("%d %b %Y")
        return f"{ad_str} ({bs_day} {month_name} {bs_year} BS)"
    else:
        return f"{bs_day} {month_name} {bs_year} BS"
