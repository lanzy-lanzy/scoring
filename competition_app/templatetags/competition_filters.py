from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg) / 100.0  # Divide by 100 since weight is in percentage
    except (ValueError, TypeError):
        return 0
