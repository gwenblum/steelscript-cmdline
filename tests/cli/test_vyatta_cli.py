# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import pytest
from mock import Mock, MagicMock

from steelscript.cmdline.cli import CLIMode
from steelscript.cmdline.cli.vyatta_cli import VyattaCLI
from steelscript.cmdline import exceptions

ANY_HOST = 'vyatta'
ANY_USER = 'user1'
ANY_PASSWORD = 'password1'
ANY_UNKNOWN_MODE = 'unknown'
TRANSPORT_TELNET = 'telnet'
TRANSPORT_SSH = 'ssh'
TRANSPORT_UNKNOWN = 'unknown'

ANY_COMMAND = 'show date'
ANY_COMMAND_OUTPUT = 'Thu Sep 12 19:50:51 GMT 2013'
ANY_COMMAND_OUTPUT_DATA = '%s\n%s\n[edit]' % (ANY_COMMAND, ANY_COMMAND_OUTPUT)
ANY_ROOT_COMMAND = 'show'
ANY_UNKNOWN_LEVEL = 'unknown'
ANY_TIMEOUT = 120
ANY_NORMAL_PROMPT = '%s@%s:~$' % (ANY_USER, ANY_HOST)
ANY_ERROR_PROMPT = 'Cannot exit: configuration modified.'


@pytest.fixture
def any_vyatta_cli():
    # Need to ensure that cli.channel is a mock whether we've called
    # start or not, as mocking out start is more annoying so many tests
    # just assume a pre-existing mocked channel.  But some do call start()
    # and need it to result in a mock as well, hence the channel_class.
    cli = VyattaCLI(machine_name=ANY_HOST,
                    username=ANY_USER,
                    password=ANY_PASSWORD,
                    channel_class=MagicMock())
    cli.channel = MagicMock()
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
    fake_match.re.pattern = VyattaCLI.CLI_CONFIG_PROMPT
    return fake_match


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
