# Copyright 2009-2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import pytest
from mock import Mock, MagicMock, patch

from steelscript.cmdline.telnetchannel import TelnetChannel
from steelscript.cmdline import exceptions

ANY_HOST = 'my-sh1'
ANY_USERNAME = 'user1'
ANY_PASSWORD = 'password1'
ANY_TEXT_TO_SEND = 'show service\r'
ANY_PROMPT_RE = ['^(\x1b\[[a-zA-Z0-9]+)?(?P<name>[a-zA-Z0-9_\-.:]+) >']
ANY_PROMPT_MATCHED = 'my-sh1 >'
ANY_DATA_RECEIVED = 'Optimization Service: Running'
ANY_TIMEOUT = 120


@pytest.fixture
def any_telnet_channel():
    return TelnetChannel(ANY_HOST, ANY_USERNAME, ANY_PASSWORD)


def test_members_initialized_correctly(any_telnet_channel):
    assert any_telnet_channel._host == ANY_HOST
    assert any_telnet_channel._user == ANY_USERNAME
    assert any_telnet_channel._password == ANY_PASSWORD
    assert any_telnet_channel.channel is None


def test_start_calls_appropriate_methods(any_telnet_channel):
    any_telnet_channel._handle_init_login = MagicMock(name='method')
    with patch('steelscript.cmdline.telnetchannel.SteelScriptTelnet') as mock:
        any_telnet_channel.start()
        assert any_telnet_channel._handle_init_login.called
        assert mock.called


def test_close(any_telnet_channel):
    mock_channel = Mock()

    any_telnet_channel.channel = mock_channel
    any_telnet_channel.close()
    mock_channel.close.assert_called_once_with()

    mock_channel.reset_mock()
    any_telnet_channel.channel = None
    any_telnet_channel.close()
    assert mock_channel.close.call_count == 0


def test_handle_init_login_when_not_ask_user_and_password(any_telnet_channel):
    mock_channel = Mock()
    any_telnet_channel.channel = mock_channel
    mock_match = Mock()
    mock_channel.expect.return_value = (2, mock_match, '')
    match = any_telnet_channel._handle_init_login(ANY_PROMPT_RE, ANY_TIMEOUT)
    assert match == mock_match


def test_handle_init_login_when_ask_user_only(any_telnet_channel):
    mock_channel = Mock()
    any_telnet_channel.channel = mock_channel
    mock_match = Mock()
    mock_channel.expect.side_effect = [(0, '', ''), (2, mock_match, '')]
    match = any_telnet_channel._handle_init_login(ANY_PROMPT_RE, ANY_TIMEOUT)
    LOGIN_CMD = ANY_USERNAME + any_telnet_channel.ENTER_LINE
    mock_channel.write.assert_called_with(LOGIN_CMD)
    assert match == mock_match


def test_handle_init_login_when_ask_password_only(any_telnet_channel):
    mock_channel = Mock()
    any_telnet_channel.channel = mock_channel
    mock_match = Mock()
    mock_channel.expect.side_effect = [(1, '', ''), (2, mock_match, '')]
    match = any_telnet_channel._handle_init_login(ANY_PROMPT_RE, ANY_TIMEOUT)
    PASSWORD_CMD = ANY_PASSWORD + any_telnet_channel.ENTER_LINE
    mock_channel.write.assert_called_with(PASSWORD_CMD)
    assert match == mock_match


def test_handle_init_login_when_ask_user_and_password(any_telnet_channel):
    mock_channel = Mock()
    any_telnet_channel.channel = mock_channel
    mock_match = Mock()
    mock_channel.expect.side_effect = [(0, '', ''), (1, '', ''),
                                       (2, mock_match, '')]
    match = any_telnet_channel._handle_init_login(ANY_PROMPT_RE, ANY_TIMEOUT)
    LOGIN_CMD = ANY_USERNAME + any_telnet_channel.ENTER_LINE
    PASSWORD_CMD = ANY_PASSWORD + any_telnet_channel.ENTER_LINE
    mock_channel.write.assert_any_call(LOGIN_CMD)
    mock_channel.write.assert_called_with(PASSWORD_CMD)
    assert match == mock_match


def test_handle_init_login_raises_if_not_match(any_telnet_channel):
    mock_channel = Mock()
    any_telnet_channel.channel = mock_channel
    mock_channel.expect.side_effect = [(-1, '', '')]
    with pytest.raises(exceptions.CmdlineTimeout):
        any_telnet_channel._handle_init_login(ANY_PROMPT_RE,
                                              ANY_TIMEOUT)


def test_handle_init_login_raises_if_user_not_accepted(any_telnet_channel):
    mock_channel = Mock()
    any_telnet_channel.channel = mock_channel
    mock_channel.expect.side_effect = [(0, '', ''), (0, '', '')]
    with pytest.raises(exceptions.CmdlineTimeout):
        any_telnet_channel._handle_init_login(ANY_PROMPT_RE,
                                              ANY_TIMEOUT)


def test_handle_init_login_raises_if_password_not_accepted(any_telnet_channel):
    mock_channel = Mock()
    any_telnet_channel.channel = mock_channel
    mock_channel.expect.side_effect = [(1, '', ''), (1, '', '')]
    with pytest.raises(exceptions.CmdlineTimeout):
        any_telnet_channel._handle_init_login(ANY_PROMPT_RE,
                                              ANY_TIMEOUT)


def test_verify_connected_raises_if_channel_not_started(any_telnet_channel):
    with pytest.raises(exceptions.ConnectionError):
        any_telnet_channel._verify_connected()


def test_receive_all_calls_appropriate_methods(any_telnet_channel):
    any_telnet_channel._verify_connected = MagicMock(name='method')
    any_telnet_channel.channel = Mock()
    any_telnet_channel.receive_all()
    assert any_telnet_channel.channel.read_very_eager.called


def test_send_calls_appropriate_methods(any_telnet_channel):
    any_telnet_channel._verify_connected = MagicMock(name='method')
    any_telnet_channel.channel = Mock()
    any_telnet_channel.send(ANY_TEXT_TO_SEND)
    any_telnet_channel.channel.write.assert_called_with(ANY_TEXT_TO_SEND)


def test_expect_raise_if_match_res_is_none(any_telnet_channel):
    with pytest.raises(TypeError):
        any_telnet_channel.expect(None)


def test_expect_raise_if_match_res_is_empty(any_telnet_channel):
    with pytest.raises(TypeError):
        any_telnet_channel.expect([])


def test_expect_raises_if_not_match_before_timeout(any_telnet_channel):
    any_telnet_channel._verify_connected = MagicMock(name='method')
    any_telnet_channel.channel = Mock()
    any_telnet_channel.channel.expect.return_value = (-1, '', '')
    with pytest.raises(exceptions.CmdlineTimeout):
        any_telnet_channel.expect(ANY_PROMPT_RE)


def test_expect_returns_on_success(any_telnet_channel):
    any_telnet_channel._verify_connected = MagicMock(name='method')
    any_telnet_channel.channel = Mock()
    mock_match = Mock()
    mock_match.start.return_value = len(ANY_DATA_RECEIVED)
    mock_match.end.return_value =\
        len(ANY_DATA_RECEIVED) + len(ANY_PROMPT_MATCHED)
    raw_data = ANY_DATA_RECEIVED + ANY_PROMPT_MATCHED
    any_telnet_channel.channel.expect.return_value = (0, mock_match, raw_data)
    (data, matched) = any_telnet_channel.expect(ANY_PROMPT_RE)
    assert data == ANY_DATA_RECEIVED
    assert matched == mock_match
