# eHB Datasources

[![Circle CI](https://circleci.com/gh/chop-dbhi/ehb-datasources.svg?style=svg)](https://circleci.com/gh/chop-dbhi/ehb-datasources)

eHB Datasources provides a set of drivers or plugins for DBHi's Biorepository Portal (BRP).

There are currently three available drivers for the BRP:

* REDCap
* ThermoFisher's Nautilus
* DBHi's Phenotype Capture Application

BRP drivers provide an interface to the eHB. Drivers should generate HTML to facilitate the creation and update of records in external systems. Drivers should have the following HTML generating functions:

* `recordListForm`: Should return a string representation of an html element that allows
the user to select a record to work with if allowed, Otherwise an
appropriate html element indicating this is restricted should be shown.
* `subRecordForm`: Should return a string representation of an html form to be used as data entry for a specific record (or portion of the record).
* `subRecordSelectionForm`: Should return a string representation of an html form to be used to select additional input data forms for a specific record (i.e. form selection for REDCap). If there is only a top level form this method can just return the single form (i.e. Nautilus sample association)

## Installation

eHB Datasources is a dependency of the Biorepository Portal and should be installed in the context of that application.

eHB Datasources does have a dependency on Jinja for templating. Otherwise, if you'd like to test the package run:

`pip install -r requirements.txt`

Which will install the following dependencies:

* nose>=1.3.7,<2
* coverage>=3.7.1,<4
* nose-timer>=0.5.0,<1
* mock>=1.3,<2

Run `make` to run tests for this module.


## Todo

* Documentation on specific drivers
* Nautilus driver tests
