# Copyright 2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import pytest
from pq_cmdline.channel import Channel


def test_subclass_with_all_required_methods():
    class MyChannel(Channel):
        def send(self):
            pass

        def expect(self):
            pass

        def receive_all(self):
            pass

    mychannel = MyChannel()


def test_subclass_raise_if_send_is_not_implemented():
    class MyChannel(Channel):
        def expect(self):
            pass

        def receive_all(self):
            pass

    with pytest.raises(TypeError):
        mychannel = MyChannel()


def test_subclass_raise_if_expect_is_not_implemented():
    class MyChannel(Channel):
        def send(self):
            pass

        def receive_all(self):
            pass

    with pytest.raises(TypeError):
        mychannel = MyChannel()


def test_subclass_raise_if_receive_all_is_not_implemented():
    class MyChannel(Channel):
        def send(self):
            pass

        def expect(self):
            pass

    with pytest.raises(TypeError):
        mychannel = MyChannel()
