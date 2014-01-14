# $Id $
#
# Copyright 2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

import pytest
from pq_cmdline.transport import Transport


def test_subclass_with_all_required_methods():
    class MyTransport(Transport):
        def connect(self):
            pass

        def disconnect(self):
            pass

        def is_connected(self):
            pass

    mytransport = MyTransport()


def test_subclass_raise_if_connect_is_not_implemented():
    class MyTransport(Transport):
        def disconnect(self):
            pass

        def is_connected(self):
            pass

    with pytest.raises(TypeError):
        mytransport = MyTransport()


def test_subclass_raise_if_disconnect_is_not_implemented():
    class MyTransport(Transport):
        def connect(self):
            pass

        def is_connected(self):
            pass

    with pytest.raises(TypeError):
        mytransport = MyTransport()


def test_subclass_raise_if_is_connected_is_not_implemented():
    class MyTransport(Transport):
        def connect(self):
            pass

        def disconnect(self):
            pass

    with pytest.raises(TypeError):
        mytransport = MyTransport()
