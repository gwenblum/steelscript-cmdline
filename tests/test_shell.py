# Copyright 2009-2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import pytest
from mock import patch, Mock
from paramiko import SSHException

from pq_cmdline.shell import Shell
from pq_cmdline import exceptions

ANY_HOST = 'host1'
ANY_USER = 'user1'
ANY_PASSWORD = 'password1'
ANY_COMMAND = 'pwd'


@pytest.fixture
def any_shell():
    with patch('pq_cmdline.shell.SshProcess') as mock:
        return Shell(ANY_HOST, ANY_USER, ANY_PASSWORD)


def test_members_initialized_correctly(any_shell):
    assert any_shell._host == ANY_HOST
    assert any_shell._user == ANY_USER
    assert any_shell._password == ANY_PASSWORD
    assert any_shell.sshprocess.connect.called


def test_exec_command_raises_on_ssh_exceptions(any_shell):
    mock_channel = Mock()
    any_shell.sshprocess.transport.open_session.return_value = mock_channel
    any_shell.sshprocess.is_connected.return_value = False
    mock_channel.exec_command.side_effect = SSHException('paramiko error')
    with pytest.raises(exceptions.ConnectionError):
        any_shell.exec_command(ANY_COMMAND)
