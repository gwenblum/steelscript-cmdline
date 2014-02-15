# Copyright 2009-2013 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import pytest
import time
import select
from mock import Mock, patch

from pq_runtime.exceptions import SshError
from pq_cmdline.sshprocess import SshProcess

ANY_HOST = 'host1'
ANY_USER = 'user1'
ANY_PASSWORD = 'password1'


@pytest.fixture
def any_sshprocess():
    return SshProcess(ANY_HOST, ANY_USER, ANY_PASSWORD)


def test_members_initialized_correctly(any_sshprocess):
    assert any_sshprocess._host == ANY_HOST
    assert any_sshprocess._user == ANY_USER
    assert any_sshprocess._password == ANY_PASSWORD
    assert any_sshprocess.transport is None


def test_connect(any_sshprocess):
    with patch('pq_cmdline.sshprocess.paramiko.Transport') as mock:
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
    with pytest.raises(SshError):
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
