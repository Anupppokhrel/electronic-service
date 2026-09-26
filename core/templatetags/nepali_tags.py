from django import template
from core.nepali_date import format_bs_date

register = template.Library()

@register.filter(name='bs_date')
def bs_date_filter(value, style="standard"):
    """Formats date in Bikram Sambat (e.g. '8 Ashwin 2083 BS')."""
    return format_bs_date(value, format_style=style)

@register.filter(name='dual_date')
def dual_date_filter(value):
    """Formats date in dual AD and BS format: '24 Sep 2026 (8 Ashwin 2083 BS)'."""
    return format_bs_date(value, format_style="full")
