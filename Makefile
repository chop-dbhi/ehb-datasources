.PHONY: all test

all: test

test:
	export DJANGO_SETTINGS_MODULE=ehb_datasources.tests.settings
	nosetests --with-coverage --with-timer --cover-package=ehb_datasources
