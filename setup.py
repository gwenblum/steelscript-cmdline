#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, division

import os
import pip
import sys

from setuptools.command.test import test as TestCommand
from setuptools import find_packages
from pip.req import parse_requirements

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

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
    
def requirements():
    return [str(ir.req) for ir in parse_requirements('requirements.txt')]

def get_version():
    try:
        # pip-installed packages can get the version from the 'version.txt'
        # file, since it is included in the package MANIFEST.
        with open('version.txt', 'r') as f:
            return f.read().strip()
    except IOError:
        # since 'version.txt' is .gitignored, running setup.py (install|develop)
        # from a git repo requires a bit of bootstrapping. in this case, we use
        # the raw .git tag as the version.
        pip.main(['install', '-U', '-i http://pypi/pq/development/', 'pq-ci'])
        from pq_ci import git
        tag = git.parse_tag()
        return '-'.join([tag['version'], tag['commits'], tag['sha']])

readme = open('README.rst').read()

setup(
    name='pq_cmdline',
    version=get_version(),
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
