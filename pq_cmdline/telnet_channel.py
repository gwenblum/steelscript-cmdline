##
# $Id$
#
# Copyright 2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

# unicode_literals is not imported because telnetlib does not work well
# with unicode_literals
from __future__ import (absolute_import, print_function, division)

import logging
import telnetlib
import socket
import re

from pq_runtime.exceptions import (re_raise, CommandError, CommandTimeout,
                                   NbtError)
from pq_cmdline.channel import Channel

LOGIN_PROMPT = b'login: '
PASSWORD_PROMPT = b'assword: '
ENTER_LINE = b'\r'


class TelnetChannel(Channel):
    """
    Class represents a telnet channel, a two-way channel that allows send
    and receive data.
    """

    bash_prompt = '\[\S+ \S+\]#\s*$'

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
            match_res = [self.bash_prompt]
        elif not isinstance(match_res, list):
            match_res = [match_res, ]

        # Start channel
        self.channel = telnetlib.Telnet(self._host)

        # Log in
        (index, match, data) = self.channel.expect([LOGIN_PROMPT], timeout)
        if index == -1:
            raise CommandTimeout("Fail to match login prompt %s before timeout"
                                 % LOGIN_PROMPT)
        self._log.debug("Sending login user ...")
        self.channel.write(self._user + ENTER_LINE)

        # Now we need to detect whether password is required.
        # Some devices like steelhead may not requrie password.
        match_password = match_res
        match_password.insert(0, PASSWORD_PROMPT)
        (index, match, data) = self.channel.expect(match_password, timeout)
        if index == 0:
            self._log.debug("Sending password ...")
            self.channel.write(self._password + ENTER_LINE)
            (index, match, data) = self.channel.expect(match_res, timeout)

        if index == -1:
            raise CommandTimeout("Failed to match prompt %s before timeout"
                                 % match_res)

        self._log.info('Telnet channel to "%s" started' % self._host)
        return match

    def _verify_connected(self):
        """
        Helper function that verifies the connection has been established
        and that the transport object we are using is still connected.

        :raises CommandError: if we are not connected
        """

        if not self.channel:
            raise CommandError('Channel has not been started')

        # Send an NOP to see whether connection is still alive.
        try:
            self.channel.sock.sendall(telnetlib.IAC + telnetlib.NOP)
        except socket.error:
            re_raise(CommandError, 'Host SSH shell has been disconnected')

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
        :throw NbtError if text_to_send is None.
        """
        if text_to_send is None:
            raise NbtError('text_to_send should not be None')

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
        :raises NbtError: if match_res is None or empty.
        :return: (output, re.MatchObject) where output is the output of the
                 command (without the matched text), and MatchObject is a
                 Python re.MatchObject containing data on what was matched.

                 You may use MatchObject.string[m.start():m.end()] to recover
                 the actual matched text.

                 MatchObject.re.pattern will contain the pattern that matched,
                 which will be one of the elements of match_res passed in.
        """

        if match_res is None:
            raise NbtError('Parameter match_res is required!')

        if not match_res:
            raise NbtError('match_res should not be empty!')

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
            raise CommandTimeout("Output not match %s before timeout"
                                 % match_res)
        # Remove matched string at the end
        length = matched.start() - matched.end()
        if length < 0:
            data = data[:length]

        # Normalize carriage returns
        data = self.fixup_carriage_returns(data)

        return (data, matched)
