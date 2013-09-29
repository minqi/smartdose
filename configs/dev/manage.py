#!/usr/bin/env python
import os
import sys
import re

# Name of root project directory
PROJECT_NAME = "smartdose"

if __name__ == "__main__":
	m = r'.*/%s/?' % (PROJECT_NAME)
	cwd = os.getcwd()
	result = re.search(m, cwd)
	rootdir = cwd[:result.end()]
	sys.path.append(rootdir)

	os.environ.setdefault("DJANGO_SETTINGS_MODULE", "configs.dev.settings")

	from django.core.management import execute_from_command_line

	execute_from_command_line(sys.argv)