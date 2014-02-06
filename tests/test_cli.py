# $Id $
#
# Copyright 2009-2013 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from pq_cmdline.cli import Cli2 as Cli
from pq_cmdline.cli import CLILevel
from pq_runtime.exceptions import CommandError, CommandTimeout

import pytest
from mock import Mock, MagicMock, patch

ANY_HOST = 'sh1'
ANY_USER = 'user1'
ANY_PASSWORD = 'password1'
ANY_TERMINAL = 'console'
TRANSPORT_SSH = 'ssh'
TRANSPORT_UNKNOWN = 'any unknown type'
ANY_COMMAND = 'show date'
ANY_COMMAND_OUTPUT = 'Thu Sep 12 19:50:51 GMT 2013'
ANY_UNKNOWN_LEVEL = 'unknown'
ANY_TIMEOUT = 120


@pytest.fixture
def any_cli():
    with patch('pq_cmdline.cli.Cli2._initialize_channel'):
        cli = Cli(ANY_HOST, ANY_USER, ANY_PASSWORD, ANY_TERMINAL,
                  TRANSPORT_SSH)
        cli.channel = Mock()
        return cli


def test_current_cli_level_at_root_level(any_cli):
    mock_match = Mock()
    mock_match.re.pattern = any_cli.cli_root_prompt
    with patch('pq_cmdline.cli.Cli2._send_line_and_wait') as mock:
        mock.return_value = ('output', mock_match)
        current_level = any_cli.current_cli_level()
        assert current_level == CLILevel.root


def test_current_cli_level_at_enable_level(any_cli):
    mock_match = Mock()
    mock_match.re.pattern = any_cli.cli_enable_prompt
    with patch('pq_cmdline.cli.Cli2._send_line_and_wait') as mock:
        mock.return_value = ('output', mock_match)
        current_level = any_cli.current_cli_level()
        assert current_level == CLILevel.enable


def test_current_cli_level_at_config_level(any_cli):
    mock_match = Mock()
    mock_match.re.pattern = any_cli.cli_conf_prompt
    with patch('pq_cmdline.cli.Cli2._send_line_and_wait') as mock:
        mock.return_value = ('output', mock_match)
        current_level = any_cli.current_cli_level()
        assert current_level == CLILevel.config


def test_current_cli_level_raise_at_unknown_level(any_cli):
    mock_match = Mock()
    mock_match.re.pattern = ANY_UNKNOWN_LEVEL
    with patch('pq_cmdline.cli.Cli2._send_line_and_wait') as mock:
        mock.return_value = ('output', mock_match)
        with pytest.raises(KeyError):
            any_cli.current_cli_level()


def test_enter_level_root_from_config_level(any_cli):
    any_cli.current_cli_level = MagicMock(name='method')
    any_cli.current_cli_level.return_value = CLILevel.config
    any_cli._send_line_and_wait = MagicMock(name='method')
    any_cli.enter_level_root()
    print any_cli._send_line_and_wait.mock_calls
    any_cli._send_line_and_wait.assert_any_call(
        'exit', any_cli.cli_enable_prompt)
    any_cli._send_line_and_wait.assert_called_with(
        'disable', any_cli.cli_root_prompt)


def test_enter_level_root_from_enable_level(any_cli):
    any_cli.current_cli_level = MagicMock(name='method')
    any_cli.current_cli_level.return_value = CLILevel.enable
    any_cli._send_line_and_wait = MagicMock(name='method')
    any_cli.enter_level_root()
    any_cli._send_line_and_wait.assert_called_with(
        'disable', any_cli.cli_root_prompt)


def test_enter_level_root_when_already_at_root_level(any_cli):
    any_cli.current_cli_level = MagicMock(name='method')
    any_cli.current_cli_level.return_value = CLILevel.root
    any_cli.enter_level_root()
    assert not any_cli.channel._send_line_and_wait.called


def test_enter_level_root_raise_if_current_level_is_unknown(any_cli):
    any_cli.current_cli_level = MagicMock(name='method')
    any_cli.current_cli_level.return_value = ANY_UNKNOWN_LEVEL
    with pytest.raises(CommandError):
        any_cli.enter_level_root()


def test_enter_level_config_from_root_level(any_cli):
    any_cli.current_cli_level = MagicMock(name='method')
    any_cli.current_cli_level.return_value = CLILevel.root
    any_cli._send_line_and_wait = MagicMock(name='method')
    any_cli._enable = MagicMock(name='method')
    any_cli.enter_level_config()
    assert any_cli._enable.called
    any_cli._send_line_and_wait.assert_called_with(
        'config terminal', any_cli.cli_conf_prompt)


def test_enter_level_config_from_enable_level(any_cli):
    any_cli.current_cli_level = MagicMock(name='method')
    any_cli.current_cli_level.return_value = CLILevel.enable
    any_cli._send_line_and_wait = MagicMock(name='method')
    any_cli.enter_level_config()
    any_cli._send_line_and_wait.assert_called_with(
        'config terminal', any_cli.cli_conf_prompt)


def test_enter_level_config_when_already_at_config_level(any_cli):
    any_cli.current_cli_level = MagicMock(name='method')
    any_cli.current_cli_level.return_value = CLILevel.config
    any_cli._send_line_and_wait = MagicMock(name='method')
    any_cli.enter_level_config()
    assert not any_cli._send_line_and_wait.called


def test_enter_level_config_raise_if_current_level_is_unknown(any_cli):
    any_cli.current_cli_level = MagicMock(name='method')
    any_cli.current_cli_level.return_value = ANY_UNKNOWN_LEVEL
    with pytest.raises(CommandError):
        any_cli.enter_level_config()


def test_exec_command_return_data(any_cli):
    command_with_return = ANY_COMMAND + '\n'
    data = command_with_return + ANY_COMMAND_OUTPUT
    any_cli._send_line_and_wait = MagicMock(name='method')
    any_cli._send_line_and_wait.return_value = (data, 'match')
    (exitcode, output) = any_cli.exec_command(ANY_COMMAND, ANY_TIMEOUT)
    any_cli._send_line_and_wait.assert_called_with(
        ANY_COMMAND, any_cli.cli_any_prompt, timeout=ANY_TIMEOUT)
    assert output == ANY_COMMAND_OUTPUT
