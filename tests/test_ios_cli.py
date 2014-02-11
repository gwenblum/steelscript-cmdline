# $Id $
#
# Copyright 2009-2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.
from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

from pq_cmdline.ios_cli import IosCli, IOSLevel
from pq_runtime.exceptions import CommandError, NbtError

import pytest
from mock import Mock, MagicMock, patch

ANY_HOST = 'cisco-router1'
ANY_USER = 'user1'
ANY_PASSWORD = 'password1'
ANY_UNKNOWN_LEVEL = 'unknown'
ANY_SUB_INTERFACE = "gi1/1.555"
CONFIG_CMD = 'config terminal'


@pytest.fixture
def any_ios_cli():
    ios_cli = IosCli(ANY_HOST, ANY_USER, ANY_PASSWORD)
    ios_cli.channel = Mock()
    return ios_cli


def test_current_cli_level_at_root_level(any_ios_cli):
    mock_match = Mock()
    mock_match.re.pattern = any_ios_cli.cli_root_prompt
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_line_and_wait.return_value = ('output', mock_match)
    current_level = any_ios_cli.current_cli_level()
    assert current_level == IOSLevel.root


def test_current_cli_level_at_enable_level(any_ios_cli):
    mock_match = Mock()
    mock_match.re.pattern = any_ios_cli.cli_enable_prompt
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_line_and_wait.return_value = ('output', mock_match)
    current_level = any_ios_cli.current_cli_level()
    assert current_level == IOSLevel.enable


def test_current_cli_level_at_config_level(any_ios_cli):
    mock_match = Mock()
    mock_match.re.pattern = any_ios_cli.cli_conf_prompt
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_line_and_wait.return_value = ('output', mock_match)
    current_level = any_ios_cli.current_cli_level()
    assert current_level == IOSLevel.config


def test_current_cli_level_at_subif_level(any_ios_cli):
    mock_match = Mock()
    mock_match.re.pattern = any_ios_cli.cli_subif_prompt
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_line_and_wait.return_value = ('output', mock_match)
    current_level = any_ios_cli.current_cli_level()
    assert current_level == IOSLevel.subif


def test_current_cli_level_raise_at_unknown_level(any_ios_cli):
    mock_match = Mock()
    mock_match.re.pattern = ANY_UNKNOWN_LEVEL
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_line_and_wait.return_value = ('output', mock_match)
    with pytest.raises(KeyError):
        any_ios_cli.current_cli_level()


def test_enter_level_subif_from_root_level(any_ios_cli):
    any_ios_cli.current_cli_level = MagicMock(name='method')
    any_ios_cli.current_cli_level.return_value = IOSLevel.root
    any_ios_cli._enable = MagicMock(name='method')
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_line_and_wait.return_value = ('output', 'match')
    any_ios_cli.enter_level_subif(ANY_SUB_INTERFACE)
    any_ios_cli._enable.assert_called_with()
    interface_cmd = 'interface ' + ANY_SUB_INTERFACE
    any_ios_cli._send_line_and_wait.assert_called_with(
        interface_cmd, any_ios_cli.cli_subif_prompt)
    any_ios_cli._send_line_and_wait.assert_any_call(
        CONFIG_CMD, any_ios_cli.cli_conf_prompt)


def test_enter_level_subif_from_enable_level(any_ios_cli):
    any_ios_cli.current_cli_level = MagicMock(name='method')
    any_ios_cli.current_cli_level.return_value = IOSLevel.enable
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_line_and_wait.return_value = ('output', 'match')
    any_ios_cli.enter_level_subif(ANY_SUB_INTERFACE)
    interface_cmd = 'interface ' + ANY_SUB_INTERFACE
    any_ios_cli._send_line_and_wait.assert_called_with(
        interface_cmd, any_ios_cli.cli_subif_prompt)
    any_ios_cli._send_line_and_wait.assert_any_call(
        CONFIG_CMD, any_ios_cli.cli_conf_prompt)


def test_enter_level_subif_from_config_level(any_ios_cli):
    any_ios_cli.current_cli_level = MagicMock(name='method')
    any_ios_cli.current_cli_level.return_value = IOSLevel.config
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_line_and_wait.return_value = ('output', 'match')
    any_ios_cli.enter_level_subif(ANY_SUB_INTERFACE)
    interface_cmd = 'interface ' + ANY_SUB_INTERFACE
    any_ios_cli._send_line_and_wait.assert_called_with(
        interface_cmd, any_ios_cli.cli_subif_prompt)


def test_enter_level_subif_raise_if_current_level_is_unknown(any_ios_cli):
    any_ios_cli.current_cli_level = MagicMock(name='method')
    any_ios_cli.current_cli_level.return_value = ANY_UNKNOWN_LEVEL
    with pytest.raises(CommandError):
        any_ios_cli.enter_level_subif(ANY_SUB_INTERFACE)
