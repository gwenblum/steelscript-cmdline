# Copyright 2009-2013 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import pytest
import time
import select
from mock import Mock, MagicMock, patch
from testfixtures import Replacer, test_time

from pq_cmdline.ssh_channel import SshChannel
from pq_runtime.exceptions import CommandError, CommandTimeout, NbtError

ANY_TERM = 'console'
ANY_TERM_WIDTH = 120
ANY_TERM_HEIGHT = 40
ANY_TEXT_TO_SEND = 'show service\r'
ANY_PROMPT_RE = '^(\x1b\[[a-zA-Z0-9]+)?(?P<name>[a-zA-Z0-9_\-.:]+) >'
ANY_NON_PROMPT_RE = '^[A-Z]+ ####'
ANY_MATCHED_PROMPT = 'il-sh1 >'
ANY_DATA_RECEIVED = 'Optimization Service: Running'
ANY_TIMEOUT = 120


@pytest.fixture
def any_ssh_channel():
    mock_sshprocess = Mock()
    mock_sshprocess.is_connected.return_value = True
    return SshChannel(mock_sshprocess)


def test_members_initialized_correctly():
    mock_sshprocess = Mock()
    mock_sshprocess.is_connected.return_value = True
    mock_channel = Mock()
    mock_sshprocess.open_interactive_channel.return_value = mock_channel
    ssh_channel = SshChannel(mock_sshprocess, ANY_TERM, ANY_TERM_WIDTH,
                             ANY_TERM_HEIGHT)
    assert ssh_channel.sshprocess == mock_sshprocess
    assert ssh_channel.channel == mock_channel
    assert ssh_channel._term == ANY_TERM
    assert ssh_channel._term_width == ANY_TERM_WIDTH
    assert ssh_channel._term_height == ANY_TERM_HEIGHT


def test_constructor_connects_sshprocess_if_it_is_not_connected():
    mock_sshprocess = Mock()
    mock_sshprocess.is_connected.return_value = False
    ssh_channel = SshChannel(mock_sshprocess)
    assert ssh_channel.sshprocess.connect.called


def test_verify_connected_raises_if_not_connected(any_ssh_channel):
    any_ssh_channel.sshprocess.is_connected.return_value = False
    with pytest.raises(CommandError):
        any_ssh_channel._verify_connected()


def test_send_raises_if_text_to_send_is_None(any_ssh_channel):
    with pytest.raises(NbtError):
        any_ssh_channel.send(None)


def test_expect_raises_if_match_res_is_None(any_ssh_channel):
    with pytest.raises(NbtError):
        any_ssh_channel.expect(None)


def test_receive_all_returns_data_in_buffer(any_ssh_channel):
    any_ssh_channel.channel.in_buffer.empty.return_value = ANY_DATA_RECEIVED
    any_ssh_channel.channel._check_add_window.return_value = 0
    data = any_ssh_channel.receive_all()
    assert data == ANY_DATA_RECEIVED


def test_send_raises_if_channel_send_return_zero(any_ssh_channel):
    any_ssh_channel.channel.send.return_value = 0
    with pytest.raises(CommandError):
        any_ssh_channel.send(ANY_TEXT_TO_SEND)


def test_send_sends_all_text(any_ssh_channel):

    # Mock channel to send one byte per time. In this case, send_text should
    # call send() the same times as the length of the text to send
    any_ssh_channel.channel.send.return_value = 1
    length = len(ANY_TEXT_TO_SEND)
    any_ssh_channel.send(ANY_TEXT_TO_SEND)
    assert any_ssh_channel.channel.send.call_count == length


def test_send_with_empty_string(any_ssh_channel):
    any_ssh_channel.channel.send.return_value = 1
    empty_string = ''
    any_ssh_channel.send(empty_string)
    assert any_ssh_channel.channel.send.call_count == 0


def test_expect_raises_if_no_match_regex(any_ssh_channel):
    with pytest.raises(NbtError):
        any_ssh_channel.expect(None)


def test_expect_raises_if_match_regex_is_empty_list(any_ssh_channel):
    with pytest.raises(NbtError):
        any_ssh_channel.expect([])


def test_expect_raises_if_match_regex_is_empty_string(any_ssh_channel):
    with pytest.raises(NbtError):
        any_ssh_channel.expect('')


def test_expect_if_channel_returns_nothing(any_ssh_channel):
    select.select = MagicMock(name='method', return_value=([1], [], []))
    any_ssh_channel.channel.recv.return_value = ''
    with pytest.raises(CommandError):
        any_ssh_channel.expect(ANY_PROMPT_RE)


def test_expect_raises_if_channel_exits_early(any_ssh_channel):
    select.select = MagicMock(name='method', return_value=([], [], []))
    any_ssh_channel.channel.exit_status_ready.return_value = True
    with pytest.raises(CommandError):
        any_ssh_channel.expect(ANY_PROMPT_RE)


def test_expect_if_not_ready_before_timeout(any_ssh_channel):
    select.select = MagicMock(name='method', return_value=([], [], []))
    any_ssh_channel.channel.exit_status_ready.return_value = False
    with Replacer() as r:
        mock_time = test_time(delta=(ANY_TIMEOUT+1), delta_type='seconds')
        r.replace('pq_cmdline.ssh_channel.time.time', mock_time)
        with pytest.raises(CommandTimeout):
            any_ssh_channel.expect(ANY_PROMPT_RE, ANY_TIMEOUT)


def test_expect_timeout_if_no_matched_prompt(any_ssh_channel):
    select.select = MagicMock(name='method', return_value=([1], [], []))
    any_ssh_channel.channel.recv.return_value = ANY_DATA_RECEIVED
    with Replacer() as r:
        mock_time = test_time(delta=(ANY_TIMEOUT+1), delta_type='seconds')
        r.replace('pq_cmdline.ssh_channel.time.time', mock_time)
        with pytest.raises(CommandTimeout):
            any_ssh_channel.expect(ANY_PROMPT_RE, ANY_TIMEOUT)


def test_expect_return_if_prompt_matched(any_ssh_channel):
    select.select = MagicMock(name='method', return_value=([1], [], []))
    mock_return = ANY_DATA_RECEIVED + '\r\n' + ANY_MATCHED_PROMPT
    any_ssh_channel.channel.recv.return_value = mock_return
    (output, matched) = any_ssh_channel.expect(ANY_PROMPT_RE)
    assert output == ANY_DATA_RECEIVED
    assert matched.re.pattern == ANY_PROMPT_RE


def test_expect_with_two_prompt_re(any_ssh_channel):
    select.select = MagicMock(name='method', return_value=([1], [], []))
    mock_return = ANY_DATA_RECEIVED + '\n' + ANY_MATCHED_PROMPT
    any_ssh_channel.channel.recv.return_value = mock_return
    match_re_list = [ANY_NON_PROMPT_RE, ANY_PROMPT_RE]
    (output, matched) = any_ssh_channel.expect(match_re_list)
    assert output == ANY_DATA_RECEIVED
    assert matched.re.pattern == ANY_PROMPT_RE


def test_expect_returns_data_in_two_lines(any_ssh_channel):
    select.select = MagicMock(name='method', return_value=([1], [], []))
    data = ANY_DATA_RECEIVED + '\n' + ANY_DATA_RECEIVED
    mock_return = data + '\n' + ANY_MATCHED_PROMPT
    any_ssh_channel.channel.recv.return_value = mock_return
    (output, matched) = any_ssh_channel.expect(ANY_PROMPT_RE)
    assert output == data
    assert matched.re.pattern == ANY_PROMPT_RE
