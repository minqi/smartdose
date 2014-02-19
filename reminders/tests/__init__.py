__author__ = 'matthewgaba'
import pkgutil
import unittest

if __name__ == __package__:
	def suite():
		return unittest.TestLoader().discover("reminders.tests", pattern="*.py")
	for loader, module_name, is_pkg in pkgutil.walk_packages(__path__):
		module = loader.find_module(module_name).load_module(module_name)
		for name in dir(module):
			obj = getattr(module, name)
			if isinstance(obj, type) and issubclass(obj, unittest.case.TestCase):
				exec ('%s = obj' % obj.__name__)

