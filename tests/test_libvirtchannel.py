# Copyright 2009-2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import re
import pytest
import mock
import libvirt

from pq_cmdline import libvirtchannel
from pq_cmdline.libvirtchannel import LibVirtChannel
from pq_cmdline import exceptions

ANY_HOST = 'my-sh1'
ANY_USERNAME = 'user1'
ANY_PASSWORD = 'password1'
ANY_TEXT_TO_SEND_UNICODE = 'show service\r'
ANY_TEXT_TO_SEND_UTF8 = b'show service\r'
PROMPT_PREFIX = b''
ANY_PROMPT_RE = ['(^|\n|\r)[a-zA-Z0-9_\-.:]+ >']
ANY_PROMPT_MATCHED = '\namnesiac >'
ANY_DATA_CHAR = 'a'
ANY_DATA_RECEIVED = 'Optimization Service: Running'
ANY_TIMEOUT = 120

PROMPT_LOGIN = b'\nlogin: '
PROMPT_PASSWORD = b'\npassword: '
PROMPT_ROOT = b'\n# '

MATCH_LOGIN = re.search(libvirtchannel.LOGIN_PROMPT, PROMPT_LOGIN)
MATCH_PASSWORD = re.search(libvirtchannel.PASSWORD_PROMPT, PROMPT_PASSWORD)
MATCH_ROOT = re.search(libvirtchannel.ROOT_PROMPT, PROMPT_ROOT)


@pytest.fixture
def any_libvirt_channel():
    return LibVirtChannel(domain_name=ANY_HOST, user=ANY_USERNAME,
                          password=ANY_PASSWORD)


@pytest.fixture
def connected_channel(any_libvirt_channel):
    # Mocks the various bits involved in a connected but not necessarily
    # logged in channel.  This is not necessarily a valid state, but
    # frees other fixtures from having to do the basic mocking.
    any_libvirt_channel._domain = mock.Mock()
    any_libvirt_channel._conn = mock.Mock()
    any_libvirt_channel._stream = mock.Mock()
    any_libvirt_channel._verify_domain_running = mock.Mock(return_value=None)
    return any_libvirt_channel


@pytest.fixture
def logged_in_channel(connected_channel):
    connected_channel._console_logged_in = True
    connected_channel._check_console_mode = mock.Mock(return_value=MATCH_ROOT)
    return connected_channel


@pytest.fixture
def login_prompt_channel(connected_channel):
    connected_channel._check_console_mode = mock.Mock(return_value=MATCH_LOGIN)
    connected_channel.expect = mock.Mock(side_effect=(
        (MATCH_PASSWORD, ''),
        (MATCH_ROOT, ''),
    ))
    return connected_channel


@pytest.fixture
def login_no_password_channel(connected_channel):
    connected_channel._check_console_mode = mock.Mock(return_value=MATCH_LOGIN)
    connected_channel.expect = mock.Mock(side_effect=(
        (MATCH_ROOT, ''),
    ))
    return connected_channel


@pytest.fixture
def password_prompt_channel(connected_channel):
    connected_channel._check_console_mode = mock.Mock(
        return_value=MATCH_PASSWORD)
    # We expect to kick off the current session and start the login process
    # again, so there's a MATCH_LOGIN to start with here.
    connected_channel.expect = mock.Mock(side_effect=(
        (MATCH_LOGIN, ''),
        (MATCH_PASSWORD, ''),
        (MATCH_ROOT, ''),
    ))
    return connected_channel


@pytest.fixture
def initial_timeout_channel(connected_channel):
    connected_channel._check_console_mode = mock.Mock(
        side_effect=exceptions.CmdlineTimeout(
            timeout=libvirtchannel.DEFAULT_EXPECT_TIMEOUT))
    # We expect to restart the login prompt matching process after a timeout.
    connected_channel.expect = mock.Mock(side_effect=(
        (MATCH_LOGIN, ''),
        (MATCH_PASSWORD, ''),
        (MATCH_ROOT, ''),
    ))
    return connected_channel


@pytest.fixture
def double_timeout_channel(connected_channel):
    connected_channel._check_console_mode = mock.Mock(
        side_effect=exceptions.CmdlineTimeout(
            timeout=libvirtchannel.DEFAULT_EXPECT_TIMEOUT))
    connected_channel.expect = mock.Mock(
        side_effect=exceptions.CmdlineTimeout(
            timeout=libvirtchannel.DEFAULT_EXPECT_TIMEOUT))
    return connected_channel


@pytest.fixture
def bad_username_channel(connected_channel):
    connected_channel._check_console_mode = mock.Mock(return_value=MATCH_LOGIN)
    connected_channel.expect = mock.Mock(
        side_effect=exceptions.CmdlineTimeout(
            timeout=libvirtchannel.DEFAULT_EXPECT_TIMEOUT))
    return connected_channel


@pytest.fixture
def bad_password_channel(connected_channel):
    connected_channel._check_console_mode = mock.Mock(return_value=MATCH_LOGIN)
    connected_channel.expect = mock.Mock(side_effect=(
        (MATCH_PASSWORD, ''),
        exceptions.CmdlineTimeout(
            timeout=libvirtchannel.DEFAULT_EXPECT_TIMEOUT),
    ))
    return connected_channel


def test_members_initialized_correctly(any_libvirt_channel):
    assert any_libvirt_channel._domain_name == ANY_HOST
    assert any_libvirt_channel._username == ANY_USERNAME
    assert any_libvirt_channel._password == ANY_PASSWORD
    assert any_libvirt_channel._domain is None
    assert any_libvirt_channel._conn is None
    assert any_libvirt_channel._stream is None
    assert any_libvirt_channel._console_logged_in is False


def test_verify_domain_running_true(any_libvirt_channel):
        mock_domain = mock.Mock()
        mock_domain.info.return_value = [libvirt.VIR_DOMAIN_RUNNING]
        any_libvirt_channel._domain = mock_domain

        try:
            any_libvirt_channel._verify_domain_running()
        except Exception:
            assert False
        else:
            assert True


def test_verify_domain_running_false(any_libvirt_channel):
        mock_domain = mock.Mock()
        mock_domain.info.return_value = [None]
        any_libvirt_channel._domain = mock_domain

        with pytest.raises(exceptions.ConnectionError):
            any_libvirt_channel._verify_domain_running()


def test_not_connected(any_libvirt_channel):
    assert any_libvirt_channel._verify_connected() is False


def test_connected(connected_channel):
    assert connected_channel._verify_connected() is True


def test_check_console_mode_not_logged_in(any_libvirt_channel):
    any_libvirt_channel.send = mock.Mock()
    any_libvirt_channel.expect = mock.Mock()
    any_libvirt_channel.expect.return_value = (MATCH_LOGIN, '')
    prompt_list = [libvirtchannel.LOGIN_PROMPT,
                   libvirtchannel.PASSWORD_PROMPT,
                   ANY_PROMPT_RE[0]]

    matched = any_libvirt_channel._check_console_mode(ANY_PROMPT_RE,
                                                      ANY_TIMEOUT)

    any_libvirt_channel.send.assert_called_with(
        b'%s%s' % (libvirtchannel.DELETE_LINE, libvirtchannel.ENTER_LINE))
    any_libvirt_channel.expect.assert_called_with(prompt_list,
                                                  timeout=ANY_TIMEOUT)
    assert any_libvirt_channel._console_logged_in is False
    assert matched.re.pattern == libvirtchannel.LOGIN_PROMPT


def test_check_console_mode_already_logged_in(any_libvirt_channel):
    any_libvirt_channel.send = mock.Mock()
    any_libvirt_channel.expect = mock.Mock()
    m = re.search(ANY_PROMPT_RE[0], ANY_PROMPT_MATCHED)
    any_libvirt_channel.expect.return_value = (m, '')

    any_libvirt_channel._check_console_mode(ANY_PROMPT_RE, ANY_TIMEOUT)

    assert any_libvirt_channel._console_logged_in is True


def test_start_calls_appropriate_methods(any_libvirt_channel):
    with mock.patch('pq_cmdline.libvirtchannel.libvirt.open') as lvopen:
        mock_conn = mock.Mock()
        mock_stream = mock.Mock()
        mock_retval = mock.Mock()

        lvopen.return_value = mock_conn
        # newStream return gets assigned to any_libvirt_channel._domain
        mock_conn.newStream.return_value = mock_stream
        any_libvirt_channel._verify_domain_running = mock.Mock(
            return_value=True)
        any_libvirt_channel._handle_init_login = mock.Mock(
            return_value=mock_retval)

        assert any_libvirt_channel.start() is mock_retval

        mock_conn.lookupByName.assert_called_with(
            any_libvirt_channel._domain_name)
        assert any_libvirt_channel._verify_domain_running.called
        mock_conn.newStream.assert_called_with(0)
        any_libvirt_channel._domain.openConsole.assert_called_with(
            None, mock_stream, libvirt.VIR_DOMAIN_CONSOLE_FORCE)

        assert any_libvirt_channel._handle_init_login.called


# Parametrize does not seem to understand additional fixture magic,
# so unroll the fixture calls.
@pytest.mark.parametrize('channel', [
    login_prompt_channel(connected_channel(any_libvirt_channel())),
    login_no_password_channel(connected_channel(any_libvirt_channel())),
    password_prompt_channel(connected_channel(any_libvirt_channel())),
    initial_timeout_channel(connected_channel(any_libvirt_channel())),
    logged_in_channel(connected_channel(any_libvirt_channel())),
])
def test_handle_init_login(channel):
    m = channel._handle_init_login([libvirtchannel.ROOT_PROMPT],
                                   libvirtchannel.DEFAULT_EXPECT_TIMEOUT)
    assert m.re.pattern == MATCH_ROOT.re.pattern
    assert channel._console_logged_in is True


@pytest.mark.parametrize('channel', [
    double_timeout_channel(connected_channel(any_libvirt_channel())),
    bad_username_channel(connected_channel(any_libvirt_channel())),
    bad_password_channel(connected_channel(any_libvirt_channel())),
])
def test_init_login_raises(channel):
    with pytest.raises(exceptions.CmdlineTimeout):
        channel._handle_init_login([libvirtchannel.ROOT_PROMPT],
                                   libvirtchannel.DEFAULT_EXPECT_TIMEOUT)


def test_send_calls_appropriate_methods(connected_channel):
    connected_channel.send(ANY_TEXT_TO_SEND_UNICODE)
    connected_channel._stream.send.assert_called_with(ANY_TEXT_TO_SEND_UTF8)


def test_receive_all(connected_channel):

    def side_effect(handler, opaque):
        for c in ANY_DATA_RECEIVED:
            handler(None, c, opaque)

    connected_channel._stream.recvAll.side_effect = side_effect
    assert connected_channel.receive_all() == ANY_DATA_RECEIVED


def test_receive_all_empty(connected_channel):
    assert connected_channel.receive_all() == ''


def test_expect_raise_if_match_res_is_none(any_libvirt_channel):
    with pytest.raises(TypeError):
        any_libvirt_channel.expect(None)


def test_expect_raise_if_match_res_is_empty(any_libvirt_channel):
    with pytest.raises(TypeError):
        any_libvirt_channel.expect([])


def test_expect_raises_if_not_match_before_timeout(any_libvirt_channel):
    # any_libvirt_channel._verify_connected = MagicMock(name='method')
    any_libvirt_channel._stream = mock.Mock()
    any_libvirt_channel._stream.recv.return_value = ANY_DATA_CHAR
    with pytest.raises(exceptions.CmdlineTimeout):
        any_libvirt_channel.expect(ANY_PROMPT_RE, timeout=1)


def test_expect_returns_on_success(any_libvirt_channel):
    # any_libvirt_channel._verify_connected = MagicMock(name='method')
    # mock_match = mock.Mock()
    # mock_match.start.return_value = len(ANY_DATA_RECEIVED)
    # mock_match.end.return_value =\
        # len(ANY_DATA_RECEIVED) + len(ANY_PROMPT_MATCHED)
    # raw_data = ANY_DATA_RECEIVED + ANY_PROMPT_MATCHED

    # Side effect returns elements of an iterable one call at a time,
    # and strings are iterable.  So this wil return one character at a time.
    any_libvirt_channel._stream = mock.Mock()
    data = '%s%s' % (ANY_DATA_RECEIVED, ANY_PROMPT_MATCHED)
    data = data.encode('utf8')

    any_libvirt_channel._stream.recv.side_effect = data
    m = re.search(ANY_PROMPT_RE[0], ANY_PROMPT_MATCHED)

    (data, matched) = any_libvirt_channel.expect(ANY_PROMPT_RE)
    assert data == ANY_DATA_RECEIVED
    assert matched.re.pattern == m.re.pattern
