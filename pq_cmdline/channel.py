# Copyright 2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

import abc
import re


class Channel(object):
    """
    Abstract class to define common interface for a two communication channel.
    """

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def receive_all(self):
        """
        Returns all text currently in the receive buffer, effectively flushing
        it.

        :return: the text that was present in the receive queue, if any.
        """
        return

    @abc.abstractmethod
    def send(self, text_to_send):
        """
        Sends text to the channel immediately.  Does not wait for any response.

        :param text_to_send: Text to send, including command terminator(s)
                             when applicable.
        """
        pass

    @abc.abstractmethod
    def expect(self, match_res, timeout=60):
        """
        Waits for some text to be received that matches one or more regex
        patterns.

        :param match_res: A list of regex pattern(s) to look for to be
                          considered successful.
        :param timeout: maximum time, in seconds, to wait for a regular
                        expression match. 0 to wait forever.
        :return: (output, re.MatchObject) where output is the output of the
                 command (without the matched text), and MatchObject is a
                 Python re.MatchObject containing data on what was matched.

                 You may use MatchObject.string[m.start():m.end()] to recover
                 the actual matched text.

                 MatchObject.re.pattern will contain the pattern that matched,
                 which will be one of the elements of match_res passed in.
        """
        return

    ### Helper methods ###################
    def safe_line_feeds(self, in_string):
        """
        :param in_string: string to replace linefeeds
        :return: a string that has the linefeeds converted to ASCII
                representation for printing
        """

        out_string = in_string.replace('\n', '\\n')
        out_string = out_string.replace('\r', '\\r')

        return out_string

    def fixup_carriage_returns(self, data):
        """
        To work around all the different \r\n combos we are
        getting from the CLI, we normalize it as:

        1) Eat consecutive \r's               (a\r\r\nb -> a\r\nb)
        2) Convert \r\n's to \n               (a\r\nb -> a\nb)
        3) Convert \n\r to \n                 (a\r\n\rb) -> (a\n\rb) -> (a\nb)
        4) Convert single \r's to \n, unless at
           end of strings                     (a\rb -> a\nb)

        #4 doesn't trigger at the end of the line to cover partially received
           data; the next character that comes in may be a \n, \r, etc.

        :param data: string to convert

        :return: the string data with the linefeeds converted into only \n's
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
