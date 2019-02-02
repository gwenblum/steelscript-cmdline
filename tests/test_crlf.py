# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import re

from steelscript.cmdline import channel


# Fill in abstract methods so we can instantiate a Channel
class FakeChannel(channel.Channel):
    def receive_all(self):
        return ''

    def send(self, text_to_send):
        pass

    def expect(self, match_res, timeout):
        return '', re.search(match_res, '')

    def _verify_connected():
        return True


def test_safe_line_feeds():
    c = FakeChannel()
    assert c.safe_line_feeds(' \n \r ') == ' \\n \\r '


def test_fixup_carriage_returns():
    c = FakeChannel()
    assert c.fixup_carriage_returns('a\r\r\nb\n\rc\n\r') == 'a\nb\nc\n\r'
