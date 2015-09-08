# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import pytest
from mock import Mock, patch

from steelscript.cmdline.sshprocess import SSHProcess
from steelscript.cmdline import exceptions

ANY_HOST = 'host1'
ANY_USER = 'user1'
ANY_PASSWORD = 'password1'
ANY_PORT = '9090'


@pytest.fixture
def any_sshprocess():
    return SSHProcess(ANY_HOST, ANY_USER, ANY_PASSWORD, ANY_PORT)


def test_members_initialized_correctly(any_sshprocess):
    assert any_sshprocess._host == ANY_HOST
    assert any_sshprocess._user == ANY_USER
    assert any_sshprocess._password == ANY_PASSWORD
    assert any_sshprocess._port == ANY_PORT
    assert any_sshprocess.transport is None


def test_connect(any_sshprocess):
    with patch('steelscript.cmdline.sshprocess.paramiko.Transport') as mock:
        mock_transport = mock.return_value
        any_sshprocess.connect()
        assert any_sshprocess.transport == mock_transport
        assert any_sshprocess.transport.start_client.called
        assert any_sshprocess.transport.auth_password.called


def test_disconnect_closes_transport(any_sshprocess):
    any_sshprocess.transport = Mock()
    any_sshprocess.disconnect()
    assert any_sshprocess.transport.close.called


def test_is_connected_if_transport_is_active(any_sshprocess):
    any_sshprocess.transport = Mock()
    any_sshprocess.transport.is_active.return_value = True
    assert any_sshprocess.is_connected()


def test_open_interactive_channel_raise_if_not_connected(any_sshprocess):
    with pytest.raises(exceptions.ConnectionError):
        any_sshprocess.open_interactive_channel()


def test_open_interactive_channel_if_connected(any_sshprocess):
    any_sshprocess.is_connected = Mock(name='method')
    any_sshprocess.is_connected.return_value = True
    any_sshprocess.transport = Mock()
    mock_channel = Mock()
    any_sshprocess.transport.open_session.return_value = mock_channel
    any_sshprocess.open_interactive_channel()
    assert any_sshprocess.transport.open_session.called
    assert mock_channel.get_pty.called
    assert mock_channel.invoke_shell.called
