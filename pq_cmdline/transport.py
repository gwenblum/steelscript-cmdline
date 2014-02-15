# Copyright 2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import absolute_import

import abc


class Transport(object):
    """
    Abstract class to define common interfaces for a transport.
    A transport is used by Cli/Shell object to handle connection setup.
    """

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def connect(self):
        """ Abstract method to start a connection """
        pass

    @abc.abstractmethod
    def disconnect(self):
        """ Abstract method to tear down current connection """
        pass

    @abc.abstractmethod
    def is_connected(self):
        """
        Check whether a connection is established or not.
        :return: True if it is connected; returns False otherwise.
        """
        return
