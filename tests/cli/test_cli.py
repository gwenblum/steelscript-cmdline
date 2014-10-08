# Copyright 2009-2013 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import pytest
from mock import Mock, MagicMock, patch

from pq_cmdline.cli import CLI, DEFAULT_MACHINE_MANAGER_URI
from pq_cmdline import exceptions
from pq_cmdline.sshchannel import SSHChannel
from pq_cmdline.telnetchannel import TelnetChannel

ANY_HOST = 'sh1'
ANY_USER = 'user1'
ANY_PASSWORD = 'password1'
ANY_TERMINAL = 'console'
ANY_MACHINE = 'sh1machine'
ANY_COMMAND = 'show date'
ANY_COMMAND_OUTPUT = 'Thu Sep 12 19:50:51 GMT 2013'
ANY_COMMAND_OUTPUT_DATA = '%s\n%s' % (ANY_COMMAND, ANY_COMMAND_OUTPUT)
ANY_ROOT_COMMAND = 'show'
ANY_UNKNOWN_LEVEL = 'unknown'
ANY_TIMEOUT = 120


@pytest.fixture
def any_cli():
    cli = CLI(hostname=ANY_HOST, username=ANY_USER, password=ANY_PASSWORD,
              terminal=ANY_TERMINAL)
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


def test_members_initialize_correctly(any_cli):
    assert any_cli._channel_args['hostname'] == ANY_HOST
    assert any_cli._channel_args['username'] == ANY_USER
    assert any_cli._channel_args['password'] == ANY_PASSWORD
    assert any_cli._channel_args['terminal'] == ANY_TERMINAL
    assert any_cli._channel_args['machine_name'] is None
    assert any_cli._channel_args['machine_manager_uri'] is \
        DEFAULT_MACHINE_MANAGER_URI
    assert any_cli._channel_class == SSHChannel
    assert any_cli.channel is None


def test_compatibility_code_by_name_ssh():
    # host and user are the differing names still in use.
    # "term" for "terminal" is not used anywhere.
    # ssh and telnet are the only transport_types used, always passed by name.
    cli = CLI(host=ANY_HOST, user=ANY_USER, password=ANY_PASSWORD,
              transport_type='ssh')
    assert cli._channel_args['hostname'] == ANY_HOST
    assert cli._channel_args['username'] == ANY_USER
    assert cli._channel_args['password'] == ANY_PASSWORD
    assert cli._channel_args['terminal'] == ANY_TERMINAL
    assert cli._channel_args['machine_name'] is None
    assert cli._channel_args['machine_manager_uri'] is \
        DEFAULT_MACHINE_MANAGER_URI
    assert cli._channel_class == SSHChannel
    assert cli.channel is None


def test_compatibility_code_by_position_telnet():
    # only the first three parameters are ever used positionally.
    # ssh and telnet are the only transport_types used, always passed by name.
    cli = CLI(ANY_HOST, ANY_USER, password=ANY_PASSWORD,
              transport_type='telnet')
    assert cli._channel_args['hostname'] == ANY_HOST
    assert cli._channel_args['username'] == ANY_USER
    assert cli._channel_args['password'] == ANY_PASSWORD
    assert cli._channel_args['terminal'] == ANY_TERMINAL
    assert cli._channel_args['machine_name'] is None
    assert cli._channel_args['machine_manager_uri'] is \
        DEFAULT_MACHINE_MANAGER_URI
    assert cli._channel_class == TelnetChannel
    assert cli.channel is None


def test_start_initialize_ssh(any_cli, prompt_match):
    cli = CLI(hostname=ANY_HOST, username=ANY_USER, password=ANY_PASSWORD,
              terminal=ANY_TERMINAL, channel_class=SSHChannel)
    with patch('pq_cmdline.cli.sshchannel.SSHChannel.__new__') as channel_new:
        cli.start()
        channel_new.assert_called_with(SSHChannel,
                                       hostname=ANY_HOST,
                                       username=ANY_USER,
                                       password=ANY_PASSWORD,
                                       prompt=None,
                                       machine_name=None,
                                       machine_manager_uri='qemu:///system',
                                       terminal=ANY_TERMINAL)


def test_start_initialize_channel_class():
    mock_channel_class = MagicMock()
    mock_channel_class
    cli = CLI(ANY_HOST, ANY_USER, ANY_PASSWORD, ANY_TERMINAL,
              channel_class=mock_channel_class)
    cli.start()
    mock_channel_class.assert_called_with(hostname=ANY_HOST,
                                          username=ANY_USER,
                                          password=ANY_PASSWORD,
                                          prompt=None,
                                          terminal=ANY_TERMINAL,
                                          machine_name=None,
                                          machine_manager_uri='qemu:///system')


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


def test_context_manger_exit_close_channel(any_cli):
    any_cli.start = MagicMock(name='method')
    mock_channel = Mock()
    any_cli.channel = mock_channel
    with any_cli:
        pass
    assert mock_channel.close.called
    assert any_cli.channel is None


def test_context_manger_exit_if_not_channel(any_cli):
    any_cli.start = MagicMock(name='method')
    mock_channel = Mock()
    any_cli.channel = mock_channel
    with any_cli:
        pass
    # If exiting didn't cause an exception, we're good.
    assert any_cli.channel is None


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
