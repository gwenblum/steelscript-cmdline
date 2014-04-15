# Copyright 2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import pytest
from mock import Mock, MagicMock

from pq_cmdline.netdevices import CLIMode
from pq_cmdline.netdevices.vyatta_cli import VyattaCli
from pq_cmdline import exceptions

ANY_HOST = 'vyatta'
ANY_USER = 'user1'
ANY_PASSWORD = 'password1'
ANY_UNKNOWN_MODE = 'unknown'
TRANSPORT_TELNET = 'telnet'
TRANSPORT_SSH = 'ssh'
TRANSPORT_UNKNOWN = 'unknown'

ANY_COMMAND = 'show date'
ANY_COMMAND_OUTPUT = 'Thu Sep 12 19:50:51 GMT 2013'
ANY_COMMAND_OUTPUT_DATA = '%s\n%s' % (ANY_COMMAND, ANY_COMMAND_OUTPUT)
ANY_ROOT_COMMAND = 'show'
ANY_UNKNOWN_LEVEL = 'unknown'
ANY_TIMEOUT = 120
ANY_NORMAL_PROMPT = '%s@%s:~$' % (ANY_USER, ANY_HOST)
ANY_ERROR_PROMPT = 'Cannot exit: configuration modified.'


@pytest.fixture
def any_vyatta_cli():
    cli = VyattaCli(ANY_HOST, ANY_USER, ANY_PASSWORD, TRANSPORT_SSH)
    cli.channel = Mock()
    return cli


@pytest.fixture
def cli_mock_output(any_vyatta_cli):
    any_vyatta_cli._send_line_and_wait = MagicMock(name='method')
    any_vyatta_cli._send_and_wait = MagicMock(name='method')
    return any_vyatta_cli


@pytest.fixture
def config_mode_match():
    fake_match = MagicMock()
    fake_match.re = MagicMock()
    fake_match.re.pattern = VyattaCli.CLI_CONFIG_PROMPT
    return fake_match


def test_members_intialize_correctly(any_vyatta_cli):
    assert any_vyatta_cli._host == ANY_HOST
    assert any_vyatta_cli._user == ANY_USER
    assert any_vyatta_cli._password == ANY_PASSWORD
    assert any_vyatta_cli._transport_type == TRANSPORT_SSH


def test_start_raises_for_unknown_transport(any_vyatta_cli):
    any_vyatta_cli._transport_type = TRANSPORT_UNKNOWN
    with pytest.raises(NotImplementedError):
        any_vyatta_cli.start()


def test_start_raises_for_transport_telnet(any_vyatta_cli):
    any_vyatta_cli._transport_type = TRANSPORT_TELNET
    with pytest.raises(NotImplementedError):
        any_vyatta_cli.start()


def test_start_initialize_ssh(any_vyatta_cli):
    any_vyatta_cli._initialize_cli_over_ssh = MagicMock(name='method')
    any_vyatta_cli.start()
    assert any_vyatta_cli._initialize_cli_over_ssh.called


def test_context_manger_enter_calls_start(any_vyatta_cli):
    any_vyatta_cli.start = MagicMock(name='method')
    with any_vyatta_cli:
        assert any_vyatta_cli.start.called


def test_use_context_manger_twice_works(any_vyatta_cli):
    any_vyatta_cli.start = MagicMock(name='method')
    with any_vyatta_cli:
        pass
    with any_vyatta_cli:
        pass
    assert any_vyatta_cli.start.call_count == 2


def test_context_manger_exit_close_transport(any_vyatta_cli):
    any_vyatta_cli.start = MagicMock(name='method')
    any_vyatta_cli._new_transport = True
    mock_transport = Mock()
    any_vyatta_cli._transport = mock_transport
    with any_vyatta_cli:
        pass
    assert mock_transport.disconnect.called
    assert any_vyatta_cli._transport is None


def test_context_manger_exit_if_not_new_transport(any_vyatta_cli):
    any_vyatta_cli.start = MagicMock(name='method')
    any_vyatta_cli._new_transport = False
    mock_transport = Mock()
    any_vyatta_cli._transport = mock_transport
    with any_vyatta_cli:
        pass
    assert not mock_transport.disconnect.called
    assert any_vyatta_cli._transport == mock_transport


def test_current_cli_mode_at_normal_mode(any_vyatta_cli):
    mock_match = Mock()
    mock_match.re.pattern = any_vyatta_cli.CLI_NORMAL_PROMPT
    any_vyatta_cli._send_line_and_wait = MagicMock(name='method')
    any_vyatta_cli._send_line_and_wait.return_value = ('output', mock_match)
    current_mode = any_vyatta_cli.current_cli_mode()
    assert current_mode == CLIMode.NORMAL


def test_current_cli_mode_at_config_mode(any_vyatta_cli):
    mock_match = Mock()
    mock_match.re.pattern = any_vyatta_cli.CLI_CONFIG_PROMPT
    any_vyatta_cli._send_line_and_wait = MagicMock(name='method')
    any_vyatta_cli._send_line_and_wait.return_value = ('output', mock_match)
    current_mode = any_vyatta_cli.current_cli_mode()
    assert current_mode == CLIMode.CONFIG


def test_current_cli_mode_raise_at_unknown_mode(any_vyatta_cli):
    mock_match = Mock()
    mock_match.re.pattern = ANY_UNKNOWN_MODE
    any_vyatta_cli._send_line_and_wait = MagicMock(name='method')
    any_vyatta_cli._send_line_and_wait.return_value = ('output', mock_match)
    with pytest.raises(exceptions.UnknownCLIMode):
        any_vyatta_cli.current_cli_mode()


def test_enter_mode_normal_from_config_mode(any_vyatta_cli):
    mock_match = Mock()
    mock_match.string = ANY_NORMAL_PROMPT
    any_vyatta_cli.current_cli_mode = MagicMock(name='method')
    any_vyatta_cli.current_cli_mode.return_value = CLIMode.CONFIG
    any_vyatta_cli._send_line_and_wait = MagicMock(name='method')
    any_vyatta_cli._send_line_and_wait.return_value = ('output', mock_match)
    any_vyatta_cli.enter_mode_normal()
    any_vyatta_cli._send_line_and_wait.assert_any_call(
        'exit',
        [any_vyatta_cli.CLI_ERROR_PROMPT, any_vyatta_cli.CLI_NORMAL_PROMPT])


def test_enter_mode_normal_raise_at_commit_pending_in_config_mode(
        any_vyatta_cli):
    mock_match = Mock()
    mock_match.string = ANY_ERROR_PROMPT
    any_vyatta_cli.current_cli_mode = MagicMock(name='method')
    any_vyatta_cli.current_cli_mode.return_value = CLIMode.CONFIG
    any_vyatta_cli._send_line_and_wait = MagicMock(name='method')
    any_vyatta_cli._send_line_and_wait.return_value = ('output', mock_match)
    with pytest.raises(exceptions.CLIError):
        any_vyatta_cli.enter_mode_normal()


def test_enter_mode_normal_from_config_mode_force(any_vyatta_cli):
    mock_match = Mock()
    mock_match.string = ANY_NORMAL_PROMPT
    any_vyatta_cli.current_cli_mode = MagicMock(name='method')
    any_vyatta_cli.current_cli_mode.return_value = CLIMode.CONFIG
    any_vyatta_cli._send_line_and_wait = MagicMock(name='method')
    any_vyatta_cli._send_line_and_wait.return_value = ('output', mock_match)
    any_vyatta_cli.enter_mode_normal(force=True)
    any_vyatta_cli._send_line_and_wait.assert_any_call(
        'exit discard', any_vyatta_cli.CLI_NORMAL_PROMPT)


def test_enter_mode_normal_when_already_at_normal_mode(any_vyatta_cli):
    any_vyatta_cli.current_cli_mode = MagicMock(name='method')
    any_vyatta_cli.current_cli_mode.return_value = CLIMode.NORMAL
    any_vyatta_cli.enter_mode_normal()
    assert not any_vyatta_cli.channel._send_line_and_wait.called


def test_enter_mode_config_from_normal_mode(any_vyatta_cli):
    any_vyatta_cli.current_cli_mode = MagicMock(name='method')
    any_vyatta_cli.current_cli_mode.return_value = CLIMode.NORMAL
    any_vyatta_cli._send_line_and_wait = MagicMock(name='method')
    any_vyatta_cli._enable = MagicMock(name='method')
    any_vyatta_cli.enter_mode_config()
    any_vyatta_cli._send_line_and_wait.assert_called_with(
        'configure', any_vyatta_cli.CLI_CONFIG_PROMPT)


def test_enter_mode_config_when_already_at_config_mode(any_vyatta_cli):
    any_vyatta_cli.current_cli_mode = MagicMock(name='method')
    any_vyatta_cli.current_cli_mode.return_value = CLIMode.CONFIG
    any_vyatta_cli._send_line_and_wait = MagicMock(name='method')
    any_vyatta_cli.enter_mode_config()
    assert not any_vyatta_cli._send_line_and_wait.called


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
