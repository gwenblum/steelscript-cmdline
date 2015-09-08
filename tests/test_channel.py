# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

from steelscript.cmdline.channel import Channel


def test_subclass_with_all_required_methods():
    class MyChannel(Channel):
        def send(self):
            pass

        def expect(self):
            pass

        def receive_all(self):
            pass

        def _verify_connected(self):
            pass

    assert isinstance(MyChannel(), MyChannel)


def test_correct_methods_required():
    assert all((Channel.send.__isabstractmethod__,
                Channel.expect.__isabstractmethod__,
                Channel.receive_all.__isabstractmethod__,
                Channel._verify_connected.__isabstractmethod__))
