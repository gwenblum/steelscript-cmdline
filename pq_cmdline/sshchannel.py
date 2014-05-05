# Copyright 2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

import time
import select
import logging
import paramiko

from pq_cmdline.channel import Channel
from pq_cmdline import exceptions


class SSHChannel(Channel):
    """
    Class represents an ssh channel, a two-way channel that allows send
    and receive data.
    """

    # Note that for the ^, Python won't accept [^] as a valid regex?
    BASH_PROMPT = '(^|\n|\r)\[\S+ \S+\]#'

    def __init__(self, sshprocess, term='console', width=80, height=24):
        """
        Create a new SSHChannel object from a SSHProcess object.

        :param sshprocess: SSHProcess object to open a channel with.
        :param term: terminal emulation to use; defaults to 'console'
        :param width: width (in characters) of the terminal screen;
                      defaults to 80
        :param height: height (in characters) of the terminal screen;
                      defaults to 24

        """

        if not sshprocess:
            raise TypeError("Parameter 'sshprocess' is required!")

        self.sshprocess = sshprocess
        self._host = self.sshprocess._host
        self._log = logging.getLogger(__name__)

        if not sshprocess.is_connected():
            sshprocess.connect()

        self._term = term
        self._term_width = width
        self._term_height = height

        # Start channel
        self.channel = \
            self.sshprocess.open_interactive_channel(term, width, height)

        self._log.info('Interactive channel to "%s" started' % self._host)

    def _verify_connected(self):
        """
        Helper function that verifies the connection has been established
        and that the transport object we are using is still connected.

        :raises ConnectionError: if we are not connected
        """

        if not self.channel:
            raise exceptions.ConnectionError(
                context='Channel has not been started')

        if not self.sshprocess.is_connected():
            raise exceptions.ConnectionError(
                context='Host SSH shell has been disconnected')

    def receive_all(self):
        """
        Returns all text currently in the receive buffer, effectively flushing
        it.

        :return: the text that was present in the receive queue, if any.
        """

        self._verify_connected()

        self._log.debug('Receiving all data')

        # Going behind Paramiko's back here; the Channel object does not have a
        # function to do this, but the BufferedPipe object that it uses to
        # store incoming data does. Note that this assumes stderr is redirected
        # to the main recv queue.
        data = self.channel.in_buffer.empty()

        # Check whether need to send a window update.
        ack = self.channel._check_add_window(len(data))

        # The number of bytes we receive is larger than in_windows_threshold,
        # send a window update. Paramiko Channel only sends window updates
        # when received bytes exceed its threshold.
        if ack > 0:
            m = paramiko.Message()
            m.add_byte(chr(paramiko.channel.MSG_CHANNEL_WINDOW_ADJUST))
            m.add_int(self.channel.remote_chanid)
            m.add_int(ack)
            self.channel.transport._send_user_message(m)

        return data

    def send(self, text_to_send):
        """
        Sends text to the channel immediately.  Does not wait for any response.

        :param text_to_send: Text to send, may be an empty string.
        :raises TypeError: if text_to_send is None.
        """
        if text_to_send is None:
            raise TypeError('text_to_send should not be None')

        self._verify_connected()

        self._log.debug('Sending "%s"' % self.safe_line_feeds(text_to_send))

        bytes_sent = 0

        while bytes_sent < len(text_to_send):
            bytes_sent_this_time = self.channel.send(text_to_send[bytes_sent:])
            if bytes_sent_this_time == 0:
                raise exceptions.ConnectionError(context='Channel is closed')
            bytes_sent += bytes_sent_this_time

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
                          Currently cannot match multiple lines.
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

        match_res, safe_match_text = self._expect_init(match_res)
        received_data = ''

        # Index into received_data marking the start of the first unprocessed
        # line.
        next_line_start = 0

        starttime = time.time()

        while True:
            # Use select to check whether channel is ready for read.
            # Reading on the channel directly would block until data is
            # ready, where select blocks at most 10 seconds which allows
            # us to check whether the specified timeout has been reached.
            # If channel is not ready for reading within 10 seconds,
            # select returns an empty list to 'readers'.
            (readers, w, x) = select.select([self.channel], [], [], 10)

            # Timeout if this is taking too long.
            if timeout and ((time.time() - starttime) > timeout):
                partial_output = repr(self.safe_line_feeds(received_data))
                raise exceptions.CmdlineTimeout(command=None,
                                                output=partial_output,
                                                timeout=timeout,
                                                failed_match=match_res)

            new_data = None

            # We did not find clear documentation in Paramiko on how to check
            # whehter a channel is closed unexpectedly. Our current logic is
            # that a channel is closed if:
            #   (1) read the channel and get 0 bytes, or
            #   (2) channel is not ready for reading but exit_status_ready()
            # Our experiments has shown that this correctly handles detecting
            # if a channel has been unexpected closed.
            if len(readers) > 0:
                new_data = self.channel.recv(4096)

                if len(new_data) == 0:
                    # Channel closed
                    raise exceptions.ConnectionError(
                        failed_match=match_res,
                        context='Channel unexpectedly closed')

                # If we're still here, we have new data to process.
                received_data, new_lines = self._process_data(
                    new_data, received_data, next_line_start)
                output, match = self._match_lines(
                    received_data, next_line_start, new_lines, match_res)

                if (output, match) != (None, None):
                    return output, match

                # Update next_line_start to be the index of the last \n
                next_line_start = received_data.rfind('\n') + 1

            elif self.channel.exit_status_ready():
                raise exceptions.ConnectionError(
                    failed_match=match_res,
                    context='Channel unexpectedly closed')

    def _process_data(self, new_data, received_data, next_line_start):
        """
        Process the new data and return updated received_data and new lines.

        :param new_data: The newly read data
        :param received_data: All data received before new_data
        :param next_line_start: Where to start splitting off the new lines.

        :return: A tuple of the updated received_data followed by the list
            of new lines.
        """
        received_data += new_data

        # The CLI does some odd things, sending multiple \r's or just a
        # \r, sometimes \r\r\n. To make this look like typical input, all
        # the \r characters with \n near them are stripped. To make
        # prompt matching easier, any \r character that does not have
        # a \n near is replaced with a \n.
        received_data = received_data[:next_line_start] + \
            self.fixup_carriage_returns(received_data[next_line_start:])

        # Take the data from next_line_start to end and split it into
        # lines so we can look for a match on each one
        new_lines = received_data[next_line_start:].splitlines()
        return received_data, new_lines

    def _match_lines(self, received_data, next_line_start,
                     new_lines, match_res):
        """
        Examine new lines for matches against our regular expressions.

        :param received_data: All data received so far, including latest.
        :param new_lines: Latest data split into individual lines.
        :param next_line_start: The point in received_data where new lines
            begin.
        :param match_res: The regular expressions for matching as documented
            for `expect()`

        :return: (output, re.MatchObject) as described for `expect() except
            that (None, None) is returned to indicate no match.
        """
        # Loop through all new lines and check them for matches.
        for line_num in range(len(new_lines)):
            match = self._find_match(new_lines[line_num], match_res)
            if match:
                self._log.debug(
                    'Matched "%s" in \n%s'
                    % (self.safe_line_feeds(match.re.pattern),
                        new_lines[line_num]))

                # Output is all data up to the next_line_start, plus
                # all lines up to the one we matched.
                output = received_data[:next_line_start] + \
                    '\n'.join(new_lines[:line_num]) + \
                    new_lines[line_num][:match.start()]
                return output, match
