#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, division

import os
import sys

from setuptools.command.test import test as TestCommand
from pip.req import parse_requirements

class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True
    def run_tests(self):
        #import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main("%s tests" % " ".join(self.test_args))
        sys.exit(errno)

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
    
def requirements():
    return [str(ir.req) for ir in parse_requirements('requirements.txt')]

readme = open('README.rst').read()

setup(
    name='pq_cmdline',
    version='0.1.0',
    description='Project Quicksilver command line interaction',
    long_description=readme,
    author='Project Quicksilver Team',
    author_email='eng-quicksilver@riverbed.com',
    packages=[
        'pq_cmdline',
    ],
    package_dir={'pq_cmdline': 'pq_cmdline'},
    include_package_data=True,
    install_requires=requirements(),
    keywords='pq_cmdline',
    tests_require=["pytest"],
    cmdclass = {'test': PyTest},
)
