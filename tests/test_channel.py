# Copyright 2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

from pq_cmdline.channel import Channel


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
