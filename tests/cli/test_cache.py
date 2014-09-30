# Copyright 2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import pytest
import mock

from pq_cmdline import cli


UNIQUE_ID = 1234
HOSTNAME = 'hostname'
USERNAME = 'username'
PASSWORD = 'password'


@pytest.fixture
def mocked_cache():
    cc = cli.CLICache()
    cc._cli_cache = mock.MagicMock()
    return cc


@pytest.fixture
def resource():
    resource = mock.MagicMock()
    resource.uniqueid = UNIQUE_ID
    resource.hostname = HOSTNAME
    resource.username = USERNAME
    resource.password = PASSWORD
    return resource


def test_construction():
    cc = cli.CLICache()
    assert cc._cli_cache == {}


def test_drop_all(mocked_cache):
    mocked_cache.drop_all()
    mocked_cache._cli_cache.clear.assert_called_once_with()


def test_drop_cli(mocked_cache, resource):
    mocked_cache.drop_cli(resource)
    mocked_cache._cli_cache.__delitem__.assert_called_once_with(UNIQUE_ID)


def test_get_cli(resource):
    cache = cli.CLICache()

    mock_cli_class = mock.MagicMock()
    mock_cli = mock.MagicMock()
    mock_cli_class.return_value = mock_cli

    c = cache.get_cli(resource, cli_class=mock_cli_class)

    mock_cli_class.assert_called_once_with(host=HOSTNAME,
                                           user=USERNAME,
                                           password=PASSWORD)
    mock_cli.start.assert_called_once_with()
    assert UNIQUE_ID in cache._cli_cache
    assert cache._cli_cache[UNIQUE_ID] is c
    assert len(cache._cli_cache) == 1

    c2 = cache.get_cli(resource, cli_class=mock_cli_class)
    # Should still have only been called once
    assert mock_cli_class.call_count == 1
    assert c2.start.call_count == 1
    assert c2 is c
    assert len(cache._cli_cache) == 1


def test_attach_cli():
    target = mock.MagicMock()
    cli.CLICache.attach_cache(target)
    assert isinstance(target.cli_cache, cli.CLICache)
