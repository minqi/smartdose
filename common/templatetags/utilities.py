from django import template

# Define template filters below
register = template.Library()
@register.filter
def divide(value, arg): 
	return float(value) / float(arg)

@register.filter
def multiply(value, arg): 
	return float(value) * float(arg)