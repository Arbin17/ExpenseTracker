from django import template

register = template.Library()

@register.filter
def abs_val(value):
    try:
        return abs(value)
    except:
        return 0

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def div(value, arg):
    """Divides the value by the argument."""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0