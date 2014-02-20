# Copyright 2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.
from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

from pq_cmdline.ios_cli import IOS_CLI, IOSMode
from pq_cmdline import exceptions

import pytest
from mock import Mock, MagicMock, patch

ANY_HOST = 'cisco-router1'
ANY_USER = 'user1'
ANY_PASSWORD = 'password1'
ANY_UNKNOWN_MODE = 'unknown'
ANY_SUB_INTERFACE = "gi1/1.555"
CONFIG_CMD = 'config terminal'


@pytest.fixture
def any_ios_cli():
    ios_cli = IOS_CLI(ANY_HOST, ANY_USER, ANY_PASSWORD)
    ios_cli.channel = Mock()
    return ios_cli


def test_current_cli_mode_at_root_mode(any_ios_cli):
    mock_match = Mock()
    mock_match.re.pattern = any_ios_cli.CLI_ROOT_PROMPT
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_line_and_wait.return_value = ('output', mock_match)
    current_mode = any_ios_cli.current_cli_mode()
    assert current_mode == IOSMode.ROOT


def test_current_cli_mode_at_enable_mode(any_ios_cli):
    mock_match = Mock()
    mock_match.re.pattern = any_ios_cli.CLI_ENABLE_PROMPT
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_line_and_wait.return_value = ('output', mock_match)
    current_mode = any_ios_cli.current_cli_mode()
    assert current_mode == IOSMode.ENABLE


def test_current_cli_mode_at_config_mode(any_ios_cli):
    mock_match = Mock()
    mock_match.re.pattern = any_ios_cli.CLI_CONF_PROMPT
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_line_and_wait.return_value = ('output', mock_match)
    current_mode = any_ios_cli.current_cli_mode()
    assert current_mode == IOSMode.CONFIG


def test_current_cli_mode_at_subif_mode(any_ios_cli):
    mock_match = Mock()
    mock_match.re.pattern = any_ios_cli.CLI_SUBIF_PROMPT
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_line_and_wait.return_value = ('output', mock_match)
    current_mode = any_ios_cli.current_cli_mode()
    assert current_mode == IOSMode.SUBIF


def test_current_cli_mode_raise_at_unknown_mode(any_ios_cli):
    mock_match = Mock()
    mock_match.re.pattern = ANY_UNKNOWN_MODE
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_line_and_wait.return_value = ('output', mock_match)
    with pytest.raises(exceptions.UnknownCLIMode):
        any_ios_cli.current_cli_mode()


def test_enter_mode_subif_from_root_mode(any_ios_cli):
    any_ios_cli.current_cli_mode = MagicMock(name='method')
    any_ios_cli.current_cli_mode.return_value = IOSMode.ROOT
    any_ios_cli._enable = MagicMock(name='method')
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_line_and_wait.return_value = ('output', 'match')
    any_ios_cli.enter_mode_subif(ANY_SUB_INTERFACE)
    any_ios_cli._enable.assert_called_with()
    interface_cmd = 'interface ' + ANY_SUB_INTERFACE
    any_ios_cli._send_line_and_wait.assert_called_with(
        interface_cmd, any_ios_cli.CLI_SUBIF_PROMPT)
    any_ios_cli._send_line_and_wait.assert_any_call(
        CONFIG_CMD, any_ios_cli.CLI_CONF_PROMPT)


def test_enter_mode_subif_from_enable_mode(any_ios_cli):
    any_ios_cli.current_cli_mode = MagicMock(name='method')
    any_ios_cli.current_cli_mode.return_value = IOSMode.ENABLE
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_line_and_wait.return_value = ('output', 'match')
    any_ios_cli.enter_mode_subif(ANY_SUB_INTERFACE)
    interface_cmd = 'interface ' + ANY_SUB_INTERFACE
    any_ios_cli._send_line_and_wait.assert_called_with(
        interface_cmd, any_ios_cli.CLI_SUBIF_PROMPT)
    any_ios_cli._send_line_and_wait.assert_any_call(
        CONFIG_CMD, any_ios_cli.CLI_CONF_PROMPT)


def test_enter_mode_subif_from_config_mode(any_ios_cli):
    any_ios_cli.current_cli_mode = MagicMock(name='method')
    any_ios_cli.current_cli_mode.return_value = IOSMode.CONFIG
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_line_and_wait.return_value = ('output', 'match')
    any_ios_cli.enter_mode_subif(ANY_SUB_INTERFACE)
    interface_cmd = 'interface ' + ANY_SUB_INTERFACE
    any_ios_cli._send_line_and_wait.assert_called_with(
        interface_cmd, any_ios_cli.CLI_SUBIF_PROMPT)


def test_enter_mode_subif_raise_if_current_mode_is_unknown(any_ios_cli):
    mock_match = Mock()
    mock_match.re.pattern = ANY_UNKNOWN_MODE
    with patch('pq_cmdline.ios_cli.IOS_CLI._send_line_and_wait') as mock:
        mock.return_value = ('output', mock_match)
        with pytest.raises(exceptions.UnknownCLIMode):
            any_ios_cli.enter_mode_subif(ANY_SUB_INTERFACE)
