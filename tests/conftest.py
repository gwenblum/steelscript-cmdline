# conftest.py for pq_cmdline tests.
#
# Copyright 2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

import pytest

# Needed to add options for passing commands for the tests.
def pytest_addoption(parser):
    parser.addoption("--host", action="store", help="host name")
    parser.addoption("--user", action="store", help="User name")
    parser.addoption("--password", action="store", help="Password")
