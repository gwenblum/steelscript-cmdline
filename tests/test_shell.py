# Copyright 2009-2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import pytest
from mock import patch, Mock, MagicMock
from paramiko import SSHException

from pq_cmdline.shell import Shell
from pq_cmdline import exceptions

ANY_HOST = 'host1'
ANY_USER = 'user1'
ANY_PASSWORD = 'password1'
ANY_COMMAND = 'pwd'
ANY_OUTPUT = ('blah whatever', 0)
NO_OUTPUT = (None, 0)
ANY_ERROR = ('error message', -1)


@pytest.fixture
def any_shell():
    with patch('pq_cmdline.shell.SshProcess') as mock:
        return Shell(ANY_HOST, ANY_USER, ANY_PASSWORD)


@pytest.fixture
def shell_mock_output(any_shell):
    any_shell._exec_paramiko_command = MagicMock(name='method')
    return any_shell


def test_members_initialized_correctly(any_shell):
    assert any_shell._host == ANY_HOST
    assert any_shell._user == ANY_USER
    assert any_shell._password == ANY_PASSWORD
    assert any_shell.sshprocess.connect.called


def test_exec_command(shell_mock_output):
    shell_mock_output._exec_paramiko_command.return_value = ANY_OUTPUT
    assert shell_mock_output.exec_command(ANY_COMMAND) == ANY_OUTPUT[0]


def test_exec_command_raises_on_ssh_exceptions(any_shell):
    mock_channel = Mock()
    any_shell.sshprocess.transport.open_session.return_value = mock_channel
    any_shell.sshprocess.is_connected.return_value = False
    mock_channel.exec_command.side_effect = SSHException('paramiko error')
    with pytest.raises(exceptions.ConnectionError):
        any_shell.exec_command(ANY_COMMAND)


def test_exec_command_raises_on_nonzero_exit(shell_mock_output):
    shell_mock_output._exec_paramiko_command.return_value = ANY_ERROR
    with pytest.raises(exceptions.ShellError):
        shell_mock_output.exec_command(ANY_COMMAND)


def test_exec_command_error_output_on_expect_error(shell_mock_output):
    shell_mock_output._exec_paramiko_command.return_value = ANY_ERROR
    info = {}
    output = shell_mock_output.exec_command(ANY_COMMAND, expect_error=True,
                                                     exit_info=info)
    assert output == ANY_ERROR[0]
    assert info['status'] == ANY_ERROR[1]


def test_exec_command_unexpected_output(shell_mock_output):
    shell_mock_output._exec_paramiko_command.return_value = ANY_OUTPUT
    with pytest.raises(exceptions.UnexpectedOutput):
        shell_mock_output.exec_command(ANY_COMMAND, expect_output=False)


def test_exec_command_unexpected_non_output(shell_mock_output):
    shell_mock_output._exec_paramiko_command.return_value = NO_OUTPUT
    with pytest.raises(exceptions.UnexpectedOutput):
        shell_mock_output.exec_command(ANY_COMMAND, expect_output=True)
