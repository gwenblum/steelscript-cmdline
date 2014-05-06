# Copyright 2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

import logging

import libvirt

from pq_cmdline import exceptions, channel

# Control-u clears any entered text.  Neat.
DELETE_LINE = b'\x15'

# Disconnect a session - Unix EOF.
DISCONNECT_SESSION = b'\x04'

# Command terminator
ENTER_LINE = b'\r'

LOGIN_PROMPT = b'login:'
PASSWORD_PROMPT = b'assword:'
ROOT_PROMPT = b'# '

PROMPT_LIST = (LOGIN_PROMPT, PASSWORD_PROMPT, ROOT_PROMPT)

DEFAULT_EXPECT_TIMEOUT = 300


class LibVirtChannel(channel.Channel):
    """
    Channel for connecting to a serial port via libvirt.

    :param domain_name: The libvirt domain to which to connect.
    :param uri: The qemu uri where the domain may be found.
    :param user: username for authentication
    :param password: password for authentication
    """

    def __init__(self, domain_name, uri='qemu:///system',
                 user='root', password=''):
        """
        Manages connection and authentication via libvirt.
        """
        self._domain_name = domain_name
        self._uri = uri
        self._domain = None
        self._conn = None
        self._stream = None
        self._console_logged_in = False

        self._username = user
        self._password = password

    def start(self, match_res=(ROOT_PROMPT,), timeout=DEFAULT_EXPECT_TIMEOUT):
        """
        Opens a console and logs in.

        :param match_res: Pattern(s) of prompts to look for.
            May be a single regex string, or a list of them.
        :param timeout: maximum time, in seconds, to wait for a regular
            expression match. 0 to wait forever.

        :return: Python re.MatchObject containing data on what was matched.
        """

        if not match_res:
            match_res = [self.ROOT_PROMPT]
        elif not (isinstance(match_res, list) or isinstance(match_res, tuple)):
            match_res = [match_res, ]

        # Get connection and libvirt domain
        self._conn = libvirt.open(self._uri)
        self._domain = self._conn.lookupByName(self._domain_name)
        if self._domain is None:
            raise exceptions.ConnectionError(
                context="Failed to find domain '%s' on host" %
                        self._domain_name)

        # Make sure domain is running
        self._verify_domain_running()

        # open console
        self._stream = self._conn.newStream(0)
        console_flags = libvirt.VIR_DOMAIN_CONSOLE_FORCE
        self._domain.openConsole(None, self._stream, console_flags)

        return self._handle_init_login(match_res, timeout)

    def _verify_domain_running(self):
        """
        Make sure domain is running.

        :raises ConnectionError: if it is not.
        """

        info = self._domain.info()
        state = info[0]
        if state != libvirt.VIR_DOMAIN_RUNNING:
            raise exceptions.ConnectionError(
                context="Domain %s is not in running state" %
                        self._domain_name)

    def _verify_connected(self):
        # TODO: Verify that the stream is really connected.
        return self._stream is not None

    def _check_console_mode(self, logged_in_prompt, timeout):
        """
        Test to see if the console is logged in
        :param logged_in_prompt: Regex for the prompt expected after login.
        :return: Match object for actual prompt received.
        """
        prompt_list = (LOGIN_PROMPT, PASSWORD_PROMPT, logged_in_prompt)

        logging.debug("Send an empty line to refresh the prompt.")
        # Clear the input buffer
        self.send(b'%s%s' % (DELETE_LINE, ENTER_LINE))
        (match, output) = self.expect(prompt_list, timeout=timeout)

        # If we did not get a username or password prompt, we are logged in
        if match.re.pattern not in [LOGIN_PROMPT, PASSWORD_PROMPT]:
            self._console_logged_in = True
        logging.debug("Console prompt = %s" %
                      match.string[match.start():match.end()])
        return match

    def _handle_init_login(self, match_res, timeout):
        """
        Login to host console.
        """
        raise NotImplementedError

    def receive_all(self):
        """
        Returns all text currently in the receive buffer, effectively flushing
        it.

        :return: the text that was present in the receive queue, if any.
        """
        raise NotImplementedError

    def send(self, text_to_send):
        """
        Sends text to the channel immediately.  Does not wait for any response.

        :param text_to_send: Text to send, including command terminator(s)
                             when applicable.
        """
        # There is also a sendAll that works like recvAll, but while
        # Python libvirt's recv still needs a length specified, its send
        # just takes the length of the supplied data automatically.
        encoded = text_to_send.encode('utf8')
        self._stream.send(encoded)

    def expect(self, match_res, timeout=DEFAULT_EXPECT_TIMEOUT):
        raise NotImplementedError
