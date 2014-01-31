# $Id $
#
# Copyright 2009-2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

import pytest
from mock import (Mock, MagicMock, patch)

from pq_cmdline.telnet_channel import (TelnetChannel, ENTER_LINE)
from pq_runtime.exceptions import (CommandError, CommandTimeout, NbtError)

ANY_HOST = 'my-sh1'
ANY_USERNAME = 'user1'
ANY_PASSWORD = 'password1'
ANY_TEXT_TO_SEND = 'show service\r'
ANY_PROMPT_RE = ['^(\x1b\[[a-zA-Z0-9]+)?(?P<name>[a-zA-Z0-9_\-.:]+) >']
ANY_PROMPT_MATCHED = 'my-sh1 >'
ANY_DATA_RECEIVED = 'Optimization Service: Running'


@pytest.fixture
def any_telnet_channel():
    return TelnetChannel(ANY_HOST, ANY_USERNAME, ANY_PASSWORD)


def test_members_initialized_correctly(any_telnet_channel):
    assert any_telnet_channel._host == ANY_HOST
    assert any_telnet_channel._user == ANY_USERNAME
    assert any_telnet_channel._password == ANY_PASSWORD
    assert any_telnet_channel.channel is None


def test_start_raises_if_no_login_prompt(any_telnet_channel):
    with patch('pq_cmdline.telnet_channel.telnetlib.Telnet') as mock:
        mock_channel = Mock()
        mock.return_value = mock_channel
        mock_channel.expect.return_value = (-1, '', '')
        with pytest.raises(CommandTimeout):
            any_telnet_channel.start()


def test_start_raises_if_no_prompt_match_after_login(any_telnet_channel):
    with patch('pq_cmdline.telnet_channel.telnetlib.Telnet') as mock:
        mock_channel = Mock()
        mock.return_value = mock_channel
        mock_channel.expect.side_effect = [(0, '', ''), (-1, '', '')]
        LOGIN_CMD = ANY_USERNAME + ENTER_LINE
        with pytest.raises(CommandTimeout):
            any_telnet_channel.start()
        mock_channel.write.assert_called_with(LOGIN_CMD)


def test_start_raises_if_no_prompt_match_after_password(any_telnet_channel):
    with patch('pq_cmdline.telnet_channel.telnetlib.Telnet') as mock:
        mock_channel = Mock()
        mock.return_value = mock_channel
        mock_channel.expect.side_effect = [(0, '', ''), (0, '', ''),
                                           (-1, '', '')]
        PASSWORD_CMD = ANY_PASSWORD + ENTER_LINE
        with pytest.raises(CommandTimeout):
            any_telnet_channel.start()
        mock_channel.write.assert_called_with(PASSWORD_CMD)


def test_start_when_password_is_not_asked(any_telnet_channel):
    with patch('pq_cmdline.telnet_channel.telnetlib.Telnet') as mock:
        mock_channel = Mock()
        mock.return_value = mock_channel
        mock_channel.expect.side_effect = [(0, '', ''), (1, '', '')]
        LOGIN_CMD = ANY_USERNAME + ENTER_LINE
        any_telnet_channel.start()
        mock_channel.write.assert_called_with(LOGIN_CMD)


def test_start_when_password_is_required(any_telnet_channel):
    with patch('pq_cmdline.telnet_channel.telnetlib.Telnet') as mock:
        mock_channel = Mock()
        mock.return_value = mock_channel
        mock_channel.expect.side_effect = [(0, '', ''), (0, '', ''),
                                           (0, '', '')]
        PASSWORD_CMD = ANY_PASSWORD + ENTER_LINE
        any_telnet_channel.start()
        mock_channel.write.assert_called_with(PASSWORD_CMD)


def test_verify_connected_raises_if_channel_not_started(any_telnet_channel):
    with pytest.raises(CommandError):
        any_telnet_channel._verify_connected()


def test_receive_all_calls_appropriate_methods(any_telnet_channel):
    any_telnet_channel._verify_connected = MagicMock(name='method')
    any_telnet_channel.channel = Mock()
    any_telnet_channel.receive_all()
    assert any_telnet_channel._verify_connected.called
    assert any_telnet_channel.channel.read_very_eager.called


def test_send_calls_appropriate_methods(any_telnet_channel):
    any_telnet_channel._verify_connected = MagicMock(name='method')
    any_telnet_channel.channel = Mock()
    any_telnet_channel.send(ANY_TEXT_TO_SEND)
    assert any_telnet_channel._verify_connected.called
    any_telnet_channel.channel.write.assert_called_with(ANY_TEXT_TO_SEND)


def test_expect_raise_if_match_res_is_none(any_telnet_channel):
    with pytest.raises(NbtError):
        any_telnet_channel.expect(None)


def test_expect_raise_if_match_res_is_empty(any_telnet_channel):
    with pytest.raises(NbtError):
        any_telnet_channel.expect([])


def test_expect_raises_if_not_match_before_timeout(any_telnet_channel):
    any_telnet_channel._verify_connected = MagicMock(name='method')
    any_telnet_channel.channel = Mock()
    any_telnet_channel.channel.expect.return_value = (-1, '', '')
    with pytest.raises(CommandTimeout):
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
