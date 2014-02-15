# Copyright 2009-2013 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

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
TRANSPORT_TELNET = 'telnet'
TRANSPORT_UNKNOWN = 'any unknown type'
ANY_COMMAND = 'show date'
ANY_COMMAND_OUTPUT = 'Thu Sep 12 19:50:51 GMT 2013'
ANY_UNKNOWN_LEVEL = 'unknown'
ANY_TIMEOUT = 120


@pytest.fixture
def any_cli():
    cli = Cli(ANY_HOST, ANY_USER, ANY_PASSWORD, ANY_TERMINAL, TRANSPORT_SSH)
    cli.channel = Mock()
    return cli


def test_members_intialize_correctly(any_cli):
    assert any_cli._host == ANY_HOST
    assert any_cli._user == ANY_USER
    assert any_cli._password == ANY_PASSWORD
    assert any_cli._terminal == ANY_TERMINAL
    assert any_cli._transport_type == TRANSPORT_SSH


def test_start_raises_for_unknown_transport(any_cli):
    any_cli._transport_type = TRANSPORT_UNKNOWN
    with pytest.raises(NotImplementedError):
        any_cli.start()


def test_start_initialize_telnet(any_cli):
    any_cli._transport_type = TRANSPORT_TELNET
    any_cli._initialize_cli_over_telnet = MagicMock(name='method')
    any_cli.start()
    assert any_cli._initialize_cli_over_telnet.called


def test_start_initialize_ssh(any_cli):
    any_cli._initialize_cli_over_ssh = MagicMock(name='method')
    any_cli.start()
    assert any_cli._initialize_cli_over_ssh.called


def test_context_manger_enter_calls_start(any_cli):
    any_cli.start = MagicMock(name='method')
    with any_cli:
        assert any_cli.start.called


def test_use_context_manger_twice_works(any_cli):
    any_cli.start = MagicMock(name='method')
    with any_cli as cli1:
        pass
    with any_cli as cli2:
        pass
    assert any_cli.start.call_count == 2


def test_context_manger_exit_close_transport(any_cli):
    any_cli.start = MagicMock(name='method')
    any_cli._new_transport = True
    mock_transport = Mock()
    any_cli._transport = mock_transport
    with any_cli:
        pass
    assert mock_transport.disconnect.called
    assert any_cli._transport is None


def test_context_manger_exit_if_not_new_transport(any_cli):
    any_cli.start = MagicMock(name='method')
    any_cli._new_transport = False
    mock_transport = Mock()
    any_cli._transport = mock_transport
    with any_cli:
        pass
    assert not mock_transport.disconnect.called
    assert any_cli._transport == mock_transport


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
