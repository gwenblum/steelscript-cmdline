# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import pytest
from mock import patch

from steelscript.cmdline.telnetchannel import SteelScriptTelnet

ANY_MSG_WITH_ARGS = 'send %s'
ANY_STR_SENT = 'any command'
EXPECT_MSG = ANY_MSG_WITH_ARGS % ANY_STR_SENT
ANY_HOST = 'my_sh1'
ANY_PORT = 22
PREFIX = 'Telnet(%s,%d):' % (ANY_HOST, ANY_PORT)


@pytest.fixture
def any_telnet():
    return SteelScriptTelnet()


def test_msg_with_args(any_telnet):
    any_telnet.host = ANY_HOST
    any_telnet.port = ANY_PORT
    with patch('steelscript.cmdline.telnetchannel.logging') as mock:
        any_telnet.msg(ANY_MSG_WITH_ARGS, ANY_STR_SENT)
        msg = PREFIX + EXPECT_MSG
        assert mock.debug.called_with(msg)


def test_msg_without_args(any_telnet):
    any_telnet.host = ANY_HOST
    any_telnet.port = ANY_PORT
    with patch('steelscript.cmdline.telnetchannel.logging') as mock:
        any_telnet.msg(ANY_STR_SENT)
        msg = PREFIX + ANY_STR_SENT
        assert mock.debug.called_with(msg)
