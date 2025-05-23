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
