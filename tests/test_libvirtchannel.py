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
ANY_PROMPT_RE = ['^(\x1b\[[a-zA-Z0-9]+)?(?P<name>[a-zA-Z0-9_\-.:]+) >']
ANY_PROMPT_MATCHED = 'amnesiac >'
ANY_DATA_CHAR = 'a'
ANY_DATA_RECEIVED = 'Optimization Service: Running'
ANY_TIMEOUT = 120


@pytest.fixture
def any_libvirt_channel():
    return LibVirtChannel(domain_name=ANY_HOST, user=ANY_USERNAME,
                          password=ANY_PASSWORD)


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


def test_check_console_mode_not_logged_in(any_libvirt_channel):
    any_libvirt_channel.send = mock.Mock()
    any_libvirt_channel.expect = mock.Mock()
    m = re.search(libvirtchannel.LOGIN_PROMPT, 'login:')
    any_libvirt_channel.expect.return_value = (m, 'login:')
    prompt_list = (libvirtchannel.LOGIN_PROMPT,
                   libvirtchannel.PASSWORD_PROMPT,
                   ANY_PROMPT_RE[0])

    matched = any_libvirt_channel._check_console_mode(ANY_PROMPT_RE[0],
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
    any_libvirt_channel.expect.return_value = (m, ANY_PROMPT_MATCHED)

    any_libvirt_channel._check_console_mode(ANY_PROMPT_RE[0], ANY_TIMEOUT)

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


def test_send_calls_appropriate_methods(any_libvirt_channel):
    any_libvirt_channel._stream = mock.Mock()
    any_libvirt_channel.send(ANY_TEXT_TO_SEND_UNICODE)
    any_libvirt_channel._stream.send.assert_called_with(ANY_TEXT_TO_SEND_UTF8)
