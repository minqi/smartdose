import re

from django import template

from common.utilities import convert_to_e164

# Define template filters below
register = template.Library()
@register.filter
def divide(value, arg): 
	return float(value) / float(arg)

@register.filter
def multiply(value, arg): 
	return float(value) * float(arg)

@register.filter
def fancy_phonenumber(value):
	"""
	Converts numbers from +1xxxxxxxxxx to (xxx) xxx-xxxx
	"""
	prog = re.compile('\+1([0-9]{3})([0-9]{3})([0-9]{4})')
	result = prog.match(value)
	fancy_phonenumber = \
		'(' + result.group(1) + ') ' + result.group(2) + '-' + result.group(3) 
	return fancy_phonenumber