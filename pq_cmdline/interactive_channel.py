# Copyright 2013 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.
#
# Interactive channel class, able to do basic expect-type processing.

import time
import select
import logging
import paramiko
import re

from pq_runtime.exceptions import CommandError, CommandTimeout, NbtError


class InteractiveChannel(object):
    """
    Wrapper class around a Paramiko channel that has had invoke_shell called.
    This is used for interactive commands that do not exit and close the SSH
    session.
    """

    # Note that for the ^, Python won't accept [^] as a valid regex?
    bash_prompt = '(^|\n|\r)\[\S+ \S+\]#'

    def __init__(self, ssh_shell, hostname=None):
        """
        Create a new InteractiveChannel object.

        :param ssh_shell: SshShell object to open a channel with.
        :param hostname: the hostname we're connecting to. This is optional
                          and for logging purposes only. If not specified,
                          it is set to ssh_shell.host
        """

        if not ssh_shell:
            raise NbtError("Parameter 'ssh_shell' is required!")
        self.channel = None

        self.ssh_shell = ssh_shell
        if hostname:
            self.hostname = hostname
        else:
            self.hostname = self.ssh_shell.host
        self.log = logging.getLogger('%s/%s' % (self.__class__.__name__,
                                                self.hostname))

    def start(self, term='console'):
        """
        Starts the interactive shell session.

        :param term: terminal emulation to use
        """

        self.channel = self.ssh_shell.open_interactive_channel(term)
        self.log.info('Interactive channel to "%s" started' % self.hostname)

    def stop(self):
        """
        Stops the interactive shell session, closing the channel.  This object
        may be reused by calling start() again, provided the transport/shell
        remains connected.
        """

        if self.channel:
            self.log.info('Closing channel to "%s"' % self.hostname)
            self.channel.close()
            self.channel = None

    def verify_connected(self):
        """
        Helper function that verifies the connection has been established
        (start() has been called), and that the transport object we are using
        is still connected.

        :raises CommandError: if we are not connected
        """

        if not self.channel:
            raise CommandError('Channel has not been started')

        if not self.ssh_shell.is_connected():
            raise CommandError('Host SSH shell has been disconnected')

    def send_and_wait(self, text_to_send, match_text, timeout=60):
        """
        Sends some text, then blocks until some text is received that matches
        one or more patterns. Please note all old data in receive buff will
        be discarded.

        :param text_to_send: Text to send, may be empty.  Note, you are
                             responsible for your own linefeed's!
        :param match_text: Pattern(s) to look for to be considered successful.
                           May be a single regex string, or a list of them.
                           Currently cannot match multiple lines.
        :param timeout: Maximum time, in seconds, to wait for a regular
                        expression match. 0 to wait forever.

        :raises CommandError: if text_to_send or match_text is empty.

        :raises CommandTimeout: if no matching text was received before the
                                timeout expired.

        :return: (output, re.MatchObject) where output is the output of the
                 command (without the matched text), and MatchObject is a Python
                 re.MatchObject containing data on what was matched.

                 You may use MatchObject.string[m.start():m.end()] to recover
                 the actual matched text.

                 MatchObject.re.pattern will contain the pattern that matched,
                 which will be one of the elements of match_res passed in.
        """

        if not text_to_send:
            raise CommandError('Required parameter text_to_send is empty.')

        if not match_text:
            raise CommandError('Required parameter match_text is empty')

        self.verify_connected()

        # Flush the receive queue first, so there's no race condition between
        # the two calls, and we don't accidently match something received in
        # the past.
        self.receive_all()
        self.send_text(text_to_send)
        return self.wait_for_prompt(match_text, timeout)

    def receive_all(self):
        """
        Returns all text currently in the receive buffer, effectively flushing
        it.

        :return: the text that was present in the receive queue, if any.
        """

        self.verify_connected()

        self.log.debug('Receiving all data')

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

    def send_text(self, text_to_send):
        """
        Sends text to the channel immediately.  Does not wait for any response.

        :param text_to_send: Text to send, may be empty.  Note, you are
                             responsible for your own linefeed's!
        """

        self.verify_connected()

        self.log.debug('Sending "%s"' % self.__safe_line_feeds(text_to_send))

        bytes_sent = 0

        while bytes_sent < len(text_to_send):
            bytes_sent_this_time = self.channel.send(text_to_send[bytes_sent:])
            if bytes_sent_this_time == 0:
                raise CommandError('Channel is closed')
            bytes_sent += bytes_sent_this_time

    def wait_for_prompt(self, match_res, timeout=60):
        """
        Waits for some text to be received that matches one or more regex
        patterns.

        Note that data may have been received before this call and is waiting
        in the buffer; you may want to call receive_all() to flush the receive
        buffer before calling this function.

        :param match_res: Pattern(s) to look for to be considered successful.
                          May be a single regex string, or a list of them.
                          Currently cannot match multiple lines.
        :param timeout: maximum time, in seconds, to wait for a regular
                        expression match. 0 to wait forever.
        :raises NbtError: if match_res is None or empty.
        :return: (output, re.MatchObject) where output is the output of the
                 command (without the matched text), and MatchObject is a Python
                 re.MatchObject containing data on what was matched.

                 You may use MatchObject.string[m.start():m.end()] to recover
                 the actual matched text.

                 MatchObject.re.pattern will contain the pattern that matched,
                 which will be one of the elements of match_res passed in.
        """

        if match_res is None:
            raise NbtError('Parameter match_res is required!')

        if not match_res:
            raise NbtError('match_res should not be empty!')

        self.verify_connected()

        # Convert the match text to a list, if it isn't already.
        if not isinstance(match_res, list):
            match_res = [match_res, ]

        # Create a newline-free copy of the list of regexes for outputting
        # to the log. Otherwise the newlines make the output unreadable.
        safe_match_text = []
        for match in match_res:
            safe_match_text.append(self.__safe_line_feeds(match))

        self.log.debug('Waiting for %s' % str(safe_match_text))

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
                raise CommandTimeout(
                    'Did not find "%s" after %d seconds. Received data:\n%s'
                    % (str(match_res), timeout,
                        repr(self.__safe_line_feeds(received_data))))

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
                    raise CommandError('Channel unexpectedly closed ' +
                                       'waiting for "%s"' % str(match_res))

            elif self.channel.exit_status_ready():
                raise CommandError('Channel unexpectedly closed ' +
                                   'waiting for "%s"' % str(match_res))
            else:
                continue

            # If we're still here, we have new data to process.
            received_data += new_data

            # The CLI does some odd things, sending multiple \r's or just a
            # \r (which putty treats as a newline..), sometimes \r\r\n.
            # Our Perl GRiTS module uses Expect and seems to deal with this
            # for the most part, but hooking that into here is pretty
            # hard.  So, hack attempt #3 - scan the data from searchStart
            # to end, and convert all the \r | \n combos into single \n's;
            # Doubtful anyone cares about \r anyway.
            received_data = received_data[:next_line_start] + \
                self.__fixup_carriage_returns(received_data[next_line_start:])

            # Take the data from next_line_start to end and split it into
            # lines so we can look for a match on each one
            new_lines = received_data[next_line_start:].splitlines()

            # Loop through all new lines and check them for matches.
            for line_num in range(len(new_lines)):
                match = self.__find_match(new_lines[line_num], match_res)
                if match:
                    self.log.debug('Matched "%s" in \n%s'
                                   % (self.__safe_line_feeds(
                                      match.re.pattern), new_lines[line_num]))

                    # Output is all data up to the next_line_start, plus
                    # all lines up to the one we matched.
                    output = received_data[:next_line_start] + \
                        '\n'.join(new_lines[:line_num]) + \
                        new_lines[line_num][:match.start()]
                    return (output, match)

            # If we're here, there's no match.  Update next_line_start to
            # be the index of the last \n
            next_line_start = received_data.rfind('\n') + 1

    def __find_match(self, data, match_res):
        """
        Given a string and a list of match strings, see if any of the text
        matches.

        :param data: data to check for matches
        :param match_res: list of match strings

        :return: None if no match was found, or the entry in matchList that
                 was found.
        """

        for pattern in match_res:
            self.log.debug('Search "%s" in "%s"' % (pattern, data))
            match = re.search(pattern, data)
            if match:
                return match

        return None

    def __safe_line_feeds(self, in_string):
        """
        :param in_string: string to replace linefeeds
        :return: a string that has the linefeeds converted to ASCII
                representation for printing
        """

        out_string = in_string.replace('\n', '\\n')
        out_string = out_string.replace('\r', '\\r')

        return out_string

    def __fixup_carriage_returns(self, data):
        """
        Hack attempt #3 to work around all the different \r\n combos we are
        getting from the CLI.  This seems to match how PuTTY will display the
        output:

        1) Eat consecutive \r's               (a\r\r\nb -> a\r\nb)
        2) Convert \r\n's to \n               (a\r\nb -> a\nb)
        3) Convert \n\r to \n                 (a\r\n\rb) -> (a\n\rb) -> (a\nb)
        4) Convert single \r's to \n, unless at
           end of strings                     (a\rb -> a\nb)

        #4 doesn't trigger at the end of the line to cover partially received
           data; the next character that comes in may be a \n, \r, etc.

        :param data: string to convert

        :return: the string data that has the linefeeds converted into only \n's
        """

        # Not the fastest approach, but when the strings are short this should
        # be ok..

        # Eat consecutive \r's

        new_data = re.sub('\r+', '\r', data)

        # Convert \r\n to \n

        new_data = re.sub('\r\n', '\n', new_data)

        # Convert \n\r to \n, unless the \r is the end of the line

        new_data = re.sub('\n\r(?!$|\r|\n)', '\n', new_data)

        return new_data
