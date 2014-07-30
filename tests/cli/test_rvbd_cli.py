# Copyright 2009-2013 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import pytest
from mock import Mock, MagicMock, patch

from pq_cmdline.cli.rvbd_cli import RVBD_CLI
from pq_cmdline.cli import CLIMode
from pq_cmdline import exceptions

ANY_HOST = 'sh1'
ANY_USER = 'user1'
ANY_PASSWORD = 'password1'
ANY_TERMINAL = 'console'
TRANSPORT_SSH = 'ssh'
TRANSPORT_TELNET = 'telnet'
TRANSPORT_UNKNOWN = 'any unknown type'
ANY_COMMAND = 'show date'
ANY_COMMAND_OUTPUT = 'Thu Sep 12 19:50:51 GMT 2013'
ANY_COMMAND_OUTPUT_DATA = '%s\n%s' % (ANY_COMMAND, ANY_COMMAND_OUTPUT)
ANY_COMMAND_ERROR = '% Unrecognized command'
ANY_COMMAND_ERROR_DATA = '%s\n%s' % (ANY_COMMAND, ANY_COMMAND_ERROR)
ANY_ROOT_COMMAND = 'show'
ANY_UNKNOWN_LEVEL = 'unknown'
ANY_TIMEOUT = 120


@pytest.fixture
def any_cli():
    cli = RVBD_CLI(ANY_HOST, ANY_USER, ANY_PASSWORD, ANY_TERMINAL,
                   TRANSPORT_SSH)
    cli.channel = Mock()
    return cli


@pytest.fixture
def cli_mock_output(any_cli):
    any_cli._send_line_and_wait = MagicMock(name='method')
    any_cli._send_and_wait = MagicMock(name='method')
    return any_cli


@pytest.fixture
def config_mode_match():
    fake_match = MagicMock()
    fake_match.re = MagicMock()
    fake_match.re.pattern = RVBD_CLI.CLI_CONF_PROMPT
    return fake_match


def test_members_intialize_correctly(any_cli):
    assert any_cli._host == ANY_HOST
    assert any_cli._user == ANY_USER
    assert any_cli._password == ANY_PASSWORD
    assert any_cli._terminal == ANY_TERMINAL
    assert any_cli._transport_type == TRANSPORT_SSH


def test_start_calls_correct_methods(any_cli):
    with patch('pq_cmdline.cli.SSHChannel') as channel:
        channel._verify_connect = MagicMock(name='method')
        any_cli._run_cli_from_shell = MagicMock(name='method')
        any_cli.enter_mode_normal = MagicMock(name='method')
        any_cli._disable_paging = MagicMock(name='method')
        any_cli.start()
        assert any_cli._run_cli_from_shell.called
        assert any_cli.enter_mode_normal.called
        assert any_cli._disable_paging.called


def test_context_manger_enter_calls_start(any_cli):
    any_cli.start = MagicMock(name='method')
    with any_cli:
        assert any_cli.start.called


def test_use_context_manger_twice_works(any_cli):
    any_cli.start = MagicMock(name='method')
    with any_cli:
        pass
    with any_cli:
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


def test_current_cli_mode_at_shell_mode(any_cli):
    mock_match = Mock()
    mock_match.re.pattern = any_cli.CLI_SHELL_PROMPT
    with patch('pq_cmdline.cli.CLI._send_line_and_wait') as mock:
        mock.return_value = ('output', mock_match)
        current_mode = any_cli.current_cli_mode()
        assert current_mode == CLIMode.SHELL


def test_current_cli_mode_at_normal_mode(any_cli):
    mock_match = Mock()
    mock_match.re.pattern = any_cli.CLI_NORMAL_PROMPT
    with patch('pq_cmdline.cli.CLI._send_line_and_wait') as mock:
        mock.return_value = ('output', mock_match)
        current_mode = any_cli.current_cli_mode()
        assert current_mode == CLIMode.NORMAL


def test_current_cli_mode_at_enable_mode(any_cli):
    mock_match = Mock()
    mock_match.re.pattern = any_cli.CLI_ENABLE_PROMPT
    with patch('pq_cmdline.cli.CLI._send_line_and_wait') as mock:
        mock.return_value = ('output', mock_match)
        current_mode = any_cli.current_cli_mode()
        assert current_mode == CLIMode.ENABLE


def test_current_cli_mode_at_config_mode(any_cli):
    mock_match = Mock()
    mock_match.re.pattern = any_cli.CLI_CONF_PROMPT
    with patch('pq_cmdline.cli.CLI._send_line_and_wait') as mock:
        mock.return_value = ('output', mock_match)
        current_mode = any_cli.current_cli_mode()
        assert current_mode == CLIMode.CONFIG


def test_current_cli_mode_raise_at_unknown_mode(any_cli):
    mock_match = Mock()
    mock_match.re.pattern = ANY_UNKNOWN_LEVEL
    with patch('pq_cmdline.cli.CLI._send_line_and_wait') as mock:
        mock.return_value = ('output', mock_match)
        with pytest.raises(exceptions.UnknownCLIMode):
            any_cli.current_cli_mode()


def test_enter_mode_normal_from_config_mode(any_cli):
    any_cli.current_cli_mode = MagicMock(name='method')
    any_cli.current_cli_mode.return_value = CLIMode.CONFIG
    any_cli._send_line_and_wait = MagicMock(name='method')
    any_cli.enter_mode_normal()
    any_cli._send_line_and_wait.assert_any_call(
        'exit', any_cli.CLI_ENABLE_PROMPT)
    any_cli._send_line_and_wait.assert_called_with(
        'disable', any_cli.CLI_NORMAL_PROMPT)


def test_enter_mode_normal_from_enable_mode(any_cli):
    any_cli.current_cli_mode = MagicMock(name='method')
    any_cli.current_cli_mode.return_value = CLIMode.ENABLE
    any_cli._send_line_and_wait = MagicMock(name='method')
    any_cli.enter_mode_normal()
    any_cli._send_line_and_wait.assert_called_with(
        'disable', any_cli.CLI_NORMAL_PROMPT)


def test_enter_mode_normal_when_already_at_normal_mode(any_cli):
    any_cli.current_cli_mode = MagicMock(name='method')
    any_cli.current_cli_mode.return_value = CLIMode.NORMAL
    any_cli.enter_mode_normal()
    assert not any_cli.channel._send_line_and_wait.called


def test_enter_mode_normal_raise_if_current_mode_is_unknown(any_cli):
    mock_match = Mock()
    mock_match.re.pattern = ANY_UNKNOWN_LEVEL
    with patch('pq_cmdline.cli.CLI._send_line_and_wait') as mock:
        mock.return_value = ('output', mock_match)
        with pytest.raises(exceptions.UnknownCLIMode):
            any_cli.enter_mode_normal()


def test_enter_mode_shell_from_normal_mode(any_cli):
    any_cli.current_cli_mode = MagicMock(name='method')
    any_cli.current_cli_mode.return_value = CLIMode.NORMAL
    any_cli._send_line_and_wait = MagicMock(name='method')
    any_cli._enable = MagicMock(name='method')
    any_cli.exec_command = MagicMock()
    any_cli.enter_mode_shell()
    assert any_cli._enable.called
    any_cli.exec_command.assert_called_with(
        '_shell', output_expected=False, prompt=any_cli.CLI_START_PROMPT)


def test_enter_mode_config_from_normal_mode(any_cli):
    any_cli.current_cli_mode = MagicMock(name='method')
    any_cli.current_cli_mode.return_value = CLIMode.NORMAL
    any_cli._send_line_and_wait = MagicMock(name='method')
    any_cli._enable = MagicMock(name='method')
    any_cli.enter_mode_config()
    assert any_cli._enable.called
    any_cli._send_line_and_wait.assert_called_with(
        'config terminal', any_cli.CLI_CONF_PROMPT)


def test_enter_mode_config_from_enable_mode(any_cli):
    any_cli.current_cli_mode = MagicMock(name='method')
    any_cli.current_cli_mode.return_value = CLIMode.ENABLE
    any_cli._send_line_and_wait = MagicMock(name='method')
    any_cli.enter_mode_config()
    any_cli._send_line_and_wait.assert_called_with(
        'config terminal', any_cli.CLI_CONF_PROMPT)


def test_enter_mode_config_when_already_at_config_mode(any_cli):
    any_cli.current_cli_mode = MagicMock(name='method')
    any_cli.current_cli_mode.return_value = CLIMode.CONFIG
    any_cli._send_line_and_wait = MagicMock(name='method')
    any_cli.enter_mode_config()
    assert not any_cli._send_line_and_wait.called


def test_enter_mode_config_raise_if_current_mode_is_unknown(any_cli):
    mock_match = Mock()
    mock_match.re.pattern = ANY_UNKNOWN_LEVEL
    with patch('pq_cmdline.cli.CLI._send_line_and_wait') as mock:
        mock.return_value = ('output', mock_match)
        with pytest.raises(exceptions.UnknownCLIMode):
            any_cli.enter_mode_config()


def test_exec_command_output(cli_mock_output, config_mode_match):
    cmo = cli_mock_output
    cmo._send_line_and_wait.return_value = (ANY_COMMAND_OUTPUT_DATA,
                                            config_mode_match)

    assert cmo.exec_command(ANY_COMMAND) == ANY_COMMAND_OUTPUT
    assert cmo.exec_command(ANY_COMMAND,
                            output_expected=True) == ANY_COMMAND_OUTPUT
    with pytest.raises(exceptions.UnexpectedOutput):
        cmo.exec_command(ANY_COMMAND, output_expected=False)


def test_exec_command_no_output(cli_mock_output, config_mode_match):
    cmo = cli_mock_output
    cmo._send_line_and_wait.return_value = ('%s\n' % ANY_COMMAND,
                                            config_mode_match)
    assert cmo.exec_command(ANY_COMMAND) == ''
    assert cmo.exec_command(ANY_COMMAND, output_expected=False) == ''
    with pytest.raises(exceptions.UnexpectedOutput):
        cmo.exec_command(ANY_COMMAND, output_expected=True)


def test_exec_command_error(cli_mock_output, config_mode_match):
    cmo = cli_mock_output
    cmo._send_line_and_wait.return_value = (ANY_COMMAND_ERROR_DATA,
                                            config_mode_match)
    assert cmo.exec_command(ANY_COMMAND,
                            error_expected=True) == ANY_COMMAND_ERROR
    assert cmo.exec_command(ANY_COMMAND,
                            output_expected=False,
                            error_expected=True) == ANY_COMMAND_ERROR
    assert cmo.exec_command(ANY_COMMAND,
                            output_expected=True,
                            error_expected=True) == ANY_COMMAND_ERROR
    with pytest.raises(exceptions.CLIError):
        cmo.exec_command(ANY_COMMAND, output_expected=True)
    with pytest.raises(exceptions.CLIError):
        cmo.exec_command(ANY_COMMAND, output_expected=False)
    with pytest.raises(exceptions.CLIError):
        cmo.exec_command(ANY_COMMAND, output_expected=None)


def test_get_sub_command_error(cli_mock_output, config_mode_match):
    cmo = cli_mock_output
    cmo._send_and_wait.return_value = (ANY_COMMAND_ERROR_DATA,
                                       config_mode_match)
    cmo._send_line_and_wait.return_value = (ANY_COMMAND_ERROR_DATA,
                                            config_mode_match)
    with pytest.raises(exceptions.CLIError):
        cmo.get_sub_commands(ANY_ROOT_COMMAND)
