# Copyright 2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

# unicode_literals is not imported because telnetlib does not work well
# with unicode_literals
from __future__ import (absolute_import, print_function, division)

import logging
import telnetlib
import socket
import re

from pq_runtime.exceptions import re_raise
from pq_cmdline import exceptions
from pq_cmdline.channel import Channel

LOGIN_PROMPT = b'(^|\n|\r)(L|l)ogin: '
PASSWORD_PROMPT = b'(^|\n|\r)(P|p)assword: '
ENTER_LINE = b'\r'


class TelnetChannel(Channel):
    """
    Class represents a telnet channel, a two-way channel that allows send
    and receive data.
    """

    BASH_PROMPT = '\[\S+ \S+\]#\s*$'

    def __init__(self, host, user='root', password=''):
        """
        Create a Telnet Channel object.

        :param host: host/ip to telnet into
        :param user: username to log in with
        :param password: password to log in with
        """

        ## Hostname to connects
        self._host = host

        self._user = user
        self._password = password

        ## telnetlib.Telnet
        self.channel = None

        self._log = logging.getLogger(__name__)

    def start(self, match_res=None, timeout=15):
        """
        Start telnet session and log it in

        :param match_res: Pattern(s) of prompts to look for.
                          May be a single regex string, or a list of them.
        :param timeout: maximum time, in seconds, to wait for a regular
                        expression match. 0 to wait forever.
        :return: Python re.MatchObject containing data on what was matched.
        """

        if not match_res:
            match_res = [self.BASH_PROMPT]
        elif not isinstance(match_res, list):
            match_res = [match_res, ]

        # Start channel
        self.channel = telnetlib.Telnet(self._host)

        return self._handle_init_login(match_res, timeout)

    def _handle_init_login(self, match_res, timeout):
        """
        Handle init login.

        :param match_res: Pattern(s) of prompts to look for after login.
                          May be a single regex string, or a list of them.
        :param timeout: maximum time, in seconds, to wait for a regular
                        expression match. 0 to wait forever.
        :return: Python re.MatchObject containing data on what was matched
                 after login.
        """

        # Add login prompt and password prompt so that we can detect
        # what require for login
        reg_with_login_prompts = match_res
        reg_with_login_prompts.insert(0, PASSWORD_PROMPT)
        reg_with_login_prompts.insert(0, LOGIN_PROMPT)

        (index, match, data) = self.channel.expect(reg_with_login_prompts,
                                                   timeout)

        if index == 0:
            # username is required for login
            self._log.debug("Sending login user ...")
            self.channel.write(self._user + ENTER_LINE)
            (index, match, data) = self.channel.expect(reg_with_login_prompts,
                                                       timeout)
        if index == 1:
            # password is required for login
            self._log.debug("Sending password ...")
            self.channel.write(self._password + ENTER_LINE)
            (index, match, data) = self.channel.expect(reg_with_login_prompts,
                                                       timeout)
        # At this point, we should already loged in; raises exceptions if not
        if index < 0:
            raise exceptions.CmdlineTimeout(timeout=timeout,
                                            failed_match=match_res)
        elif index in (0, 1):
            self._log.info("Login failed, still waiting for %s prompt",
                           ('username' if index == 0 else 'password'))
            raise exceptions.CmdlineTimeout(timeout=timeout,
                failed_match=reg_with_login_prompts[index])

        # Login successfully if reach this point
        self._log.info('Telnet channel to "%s" started' % self._host)
        return match

    def _verify_connected(self):
        """
        Helper function that verifies the connection has been established
        and that the transport object we are using is still connected.

        :raises ConnectionError: if we are not connected
        """

        if not self.channel:
            raise exceptions.ConnectionError(
                context='Channel has not been started')

        # Send an NOP to see whether connection is still alive.
        try:
            self.channel.sock.sendall(telnetlib.IAC + telnetlib.NOP)
        except socket.error:
            # TODO: re_raise and passing kwargs not compatible.
            # re_raise(CommandError, 'Host SSH shell has been disconnected')
            self._log.info('Host SSH shell has been disconnected')
            re_raise(exceptions.ConnectionError)

    def receive_all(self):
        """
        Returns all text currently in the receive buffer, effectively flushing
        it.

        :return: the text that was present in the receive queue, if any.
        """

        self._verify_connected()

        self._log.debug('Receiving all data')

        return self.channel.read_very_eager()

    def send(self, text_to_send):
        """
        Sends text to the channel immediately.  Does not wait for any response.

        :param text_to_send: Text to send, may be an empty string.
        :raises TypeError: if text_to_send is None.
        """
        if text_to_send is None:
            raise TypeError('text_to_send should not be None')

        # Encode text to ascii; telnetlib does not work well with unicode
        # literals.
        text_to_send = text_to_send.encode('ascii')

        self._verify_connected()

        self._log.debug('Sending "%s"' % self.safe_line_feeds(text_to_send))
        self.channel.write(text_to_send)

    def expect(self, match_res, timeout=60):
        """
        Waits for some text to be received that matches one or more regex
        patterns.

        Note that data may have been received before this call and is waiting
        in the buffer; you may want to call receive_all() to flush the receive
        buffer before calling send() and call this function to match the
        output from your send() only.

        :param match_res: Pattern(s) to look for to be considered successful.
                          May be a single regex string, or a list of them.
        :param timeout: maximum time, in seconds, to wait for a regular
                        expression match. 0 to wait forever.
        :raises TypeError: if match_res is None or empty.
        :return: (output, re.MatchObject) where output is the output of the
                 command (without the matched text), and MatchObject is a
                 Python re.MatchObject containing data on what was matched.

                 You may use MatchObject.string[m.start():m.end()] to recover
                 the actual matched text.

                 MatchObject.re.pattern will contain the pattern that matched,
                 which will be one of the elements of match_res passed in.
        """

        if match_res is None:
            raise TypeError('Parameter match_res is required!')

        if not match_res:
            raise TypeError('match_res should not be empty!')

        # Convert the match text to a list, if it isn't already.
        if not isinstance(match_res, list):
            match_res = [match_res, ]

        self._verify_connected()

        # Create a newline-free copy of the list of regexes for outputting
        # to the log. Otherwise the newlines make the output unreadable.
        safe_match_text = []
        for match in match_res:
            safe_match_text.append(self.safe_line_feeds(match))

        self._log.debug('Waiting for %s' % str(safe_match_text))
        (index, matched, data) = self.channel.expect(match_res, timeout)
        if index == -1:
            raise exceptions.CmdlineTimeout(timeout=timeout,
                                            failed_match=match_res)
        # Remove matched string at the end
        length = matched.start() - matched.end()
        if length < 0:
            data = data[:length]

        # Normalize carriage returns
        data = self.fixup_carriage_returns(data)

        return (data, matched)
