.PHONY: all test

all: test

test:
	nosetests --with-coverage --with-timer --cover-package=ehb_datasources
