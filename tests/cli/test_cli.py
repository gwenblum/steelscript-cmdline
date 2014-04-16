# Copyright 2009-2013 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import pytest
from mock import Mock, MagicMock

from pq_cmdline.cli import CLI
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
ANY_ROOT_COMMAND = 'show'
ANY_UNKNOWN_LEVEL = 'unknown'
ANY_TIMEOUT = 120


@pytest.fixture
def any_cli():
    cli = CLI(ANY_HOST, ANY_USER, ANY_PASSWORD, ANY_TERMINAL, TRANSPORT_SSH)
    cli.channel = Mock()
    return cli


@pytest.fixture
def cli_mock_output(any_cli):
    any_cli._send_line_and_wait = MagicMock(name='method')
    any_cli._send_and_wait = MagicMock(name='method')
    return any_cli


@pytest.fixture
def prompt_match():
    fake_match = MagicMock()
    fake_match.re = MagicMock()
    fake_match.re.pattern = CLI.CLI_START_PROMPT
    return fake_match


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


def test_exec_command_output(cli_mock_output, prompt_match):
    cmo = cli_mock_output
    cmo._send_line_and_wait.return_value = (ANY_COMMAND_OUTPUT_DATA,
                                            prompt_match)

    assert cmo.exec_command(ANY_COMMAND) == ANY_COMMAND_OUTPUT
    assert cmo.exec_command(ANY_COMMAND,
                            output_expected=True) == ANY_COMMAND_OUTPUT
    with pytest.raises(exceptions.UnexpectedOutput):
        cmo.exec_command(ANY_COMMAND, output_expected=False)


def test_exec_command_no_output(cli_mock_output, prompt_match):
    cmo = cli_mock_output
    cmo._send_line_and_wait.return_value = ('%s\n' % ANY_COMMAND,
                                            prompt_match)
    assert cmo.exec_command(ANY_COMMAND) == ''
    assert cmo.exec_command(ANY_COMMAND, output_expected=False) == ''
    with pytest.raises(exceptions.UnexpectedOutput):
        cmo.exec_command(ANY_COMMAND, output_expected=True)
