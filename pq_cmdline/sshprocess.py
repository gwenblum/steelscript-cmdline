# Copyright 2013 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.
#
# Basic SSH shell, wrapped around Paramiko
# Modified based on codes from mgmt-fwk

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import paramiko
import logging

from pq_runtime.exceptions import re_raise
from pq_cmdline import exceptions
from pq_cmdline.transport import Transport


class SSHProcess(Transport):
    """
    SSH transport class to handle ssh connection setup.
    """

    # Seconds to wait for banner comming out after starting connection.
    BANNER_TIMEOUT = 5

    def __init__(self, host, user='root', password=''):
        """
        Initializer

        :param host: host/ip to ssh into
        :param user: username to log in with
        :param password: password to log in with
        """

        ## Hostname shell connects to
        self._host = host

        ## Username shell connects with
        self._user = user

        ## Password shell connects with
        self._password = password

        ## paramiko.Transport object, the actual SSH engine.
        # http://www.lag.net/paramiko/docs/
        self.transport = None

        ## Logging module
        self._log = logging.getLogger(__name__)

    def connect(self):
        """
        Connects to the host.

        :raises ConnectionError: on error
        """
        self._log.info('Connecting to "%s" as "%s"' % (self._host, self._user))
        try:
            self.transport = paramiko.Transport((self._host, 22))
            self.transport.banner_timeout = self.BANNER_TIMEOUT
            self.transport.start_client()
            self.transport.auth_password(self._user, self._password,
                                         fallback=True)
        except paramiko.ssh_exception.SSHException:
            # Close the session, or the child thread apparently hangs
            self.disconnect()
            # TODO: re_raise not compatibile with passing kwargs
            # re_raise(SSHError, "Could not connect to %s" % self._host)
            self._log.info("Could not connect to %s", self._host)
            re_raise(exceptions.ConnectionError)

    def disconnect(self):
        """
        Disconnects from the host
        """

        if self.transport:
            self.transport.close()

    def is_connected(self):
        """
        Check whether SSH connection is established or not.
        :return: True if it is connected; returns False otherwise.
        """
        if self.transport and self.transport.is_active():
            return True
        return False

    def open_interactive_channel(self, term='console', width=80, height=24):
        """
        Creates and starts an interactive channel that may be used to
        communicate with the remote end in a stateful way. This should be used
        over exec_command whenever the channel must remain open between
        commands for interactive processing, or when a terminal/tty is
        necessary; eg, the CLI.

        :param term: terminal type to emulate; defaults to 'console'
        :param width: width (in characters) of the terminal screen;
            defaults to 80
        :param height: height (in characters) of the terminal screen;
            defaults to 24

        :raises ConnectionError: if the SSH connection has not yet been
                                 established.

        :return: An Paramiko channel that communicate with the remote end in
                 a stateful way.
        """

        if (not self.is_connected()):
            raise exceptions.ConnectionError(context='Not connected!')

        channel = self.transport.open_session()
        channel.get_pty(term, width, height)
        channel.invoke_shell()
        channel.set_combine_stderr(True)
        return channel
