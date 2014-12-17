# -*- coding: utf-8 -*-
#
# Copyright 2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import absolute_import, print_function, division

import logging

from steelscript.cmdline import exceptions

# Command terminator
ENTER_LINE = b'\r'


class PowerShell(object):
    """
    PowerShell implementation for Windows Devices

    :param channel: underlying channel
    :type channel: :class:`steelscript.cmdline.Channel`
    """

    POWERSHELL_PROMPT = '(PS.*>)'
    """
    A generic regex which will try to match powershell prompt patterns

    Presently this does not check for the hostname.
    """

    def __init__(self, channel):
        self._log = logging.getLogger(__name__)
        self.channel = channel

    def start(self, start_prompt=None):
        """
        Initialize underlying channel.

        :param start_prompt: A non-default prompt to match, if any.
        :type start_prompt: regex pattern
        """

        # Wait for a prompt, try and figure out where we are.  It's a new
        # channel so we should only be at bash or the main CLI prompt.
        if start_prompt is None:
            start_prompt = self.POWERSHELL_PROMPT
        self.channel.start(start_prompt)

    def _send_line_and_wait(self, text_to_send, match_res, timeout=60):
        """
        Discard old data in buffer, sends data, then blocks until some text is
        received that matches one or more patterns.

        :param text_to_send: Text to send, may be empty. A newline will be
                             automatically appended.
        :param match_res: Pattern(s) to look for to be considered successful.
        :param timeout: Maximum time, in seconds, to wait for a regular
                        expression match. 0 to wait forever.

        :return: ``(output, match_object)`` where output is the output of the
            command (without the matched text), and match_object is a
            Python :class:`re.MatchObject` containing data on what was matched.
        """
        self.channel.receive_all()
        self.channel.send(text_to_send + ENTER_LINE)
        return self.channel.expect(match_res, timeout)

    def exec_command(self, command, timeout=60, output_expected=None):
        """
        Executes the given command.

        This method handles detecting simple boolean conditions such as
        the presence of output or errors.

        :param command:  command to execute, newline appended automatically
        :param timeout:  maximum time, in seconds, to wait for the command to
            finish. 0 to wait forever.
        :param output_expected: If not None, indicates whether output is
            expected (True) or no output is expected (False).
            If the opposite occurs, raise UnexpectedOutput. Default is None.
        :type output_expected: bool or None

        :raises TypeError: if output_expected type is incorrect
        :raises CmdlineTimeout: on timeout
        :raises UnexpectedOutput: if output occurs when no output was
            expected, or no output occurs when output was expected

        :return: output of the command, minus the command itself.
        """

        if output_expected is not None and not isinstance(
                output_expected, bool):
            raise TypeError("exec_command: output_expected requires a boolean "
                            "value or None")

        self._log.debug('Executing cmd "%s"' % command)

        (output, match) = self._send_line_and_wait(command,
                                                   [self.POWERSHELL_PROMPT],
                                                   timeout=timeout)

        # CLI adds on escape chars and such sometimes, so to remove the command
        # we just send from the output, split the output into lines, then
        # rejoin it with the first line removed.
        output = '\n'.join(output.splitlines()[1:])

        if ((output_expected is not None) and (bool(output) !=
                                               bool(output_expected))):
            raise exceptions.UnexpectedOutput(command=command,
                                              output=output,
                                              expected_output=output_expected)
        return output
