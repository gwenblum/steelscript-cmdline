# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import pytest
from steelscript.cmdline.transport import Transport


def test_subclass_with_all_required_methods():
    class MyTransport(Transport):
        def connect(self):
            pass

        def disconnect(self):
            pass

        def is_connected(self):
            pass

    MyTransport()


def test_subclass_raise_if_connect_is_not_implemented():
    class MyTransport(Transport):
        def disconnect(self):
            pass

        def is_connected(self):
            pass

    with pytest.raises(TypeError):
        MyTransport()


def test_subclass_raise_if_disconnect_is_not_implemented():
    class MyTransport(Transport):
        def connect(self):
            pass

        def is_connected(self):
            pass

    with pytest.raises(TypeError):
        MyTransport()


def test_subclass_raise_if_is_connected_is_not_implemented():
    class MyTransport(Transport):
        def connect(self):
            pass

        def disconnect(self):
            pass

    with pytest.raises(TypeError):
        MyTransport()
