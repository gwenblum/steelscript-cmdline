# Copyright 2013 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import logging

from pq_cmdline.sshchannel import SSHChannel
from pq_cmdline.sshprocess import SSHProcess
from pq_cmdline.telnetchannel import TelnetChannel
from pq_cmdline.libvirtchannel import LibVirtChannel
from pq_cmdline import exceptions

# Control-u clears any entered text.  Neat.
DELETE_LINE = b'\x15'

# Command terminator
ENTER_LINE = b'\r'


class CLIMode(object):

    """
    Different config modes the CLI can be in
    """
    SHELL = 'shell'
    NORMAL = 'normal'
    ENABLE = 'enable'
    CONFIG = 'configure'
    SUBIF = 'subif'


class CLI(object):

    """
    Base class CLI implementation for Network Devices
    Vendor specific CLI's can inherit from this base class. This class by
    itself will try to work on a generic CLI if vendor specific class is not
    present.
    """

    # Presently the CLI_START_PROMPT is a generic regex which will try to
    # match prompt patterns, without having a check for hostname
    # there is a possiblity there might be false positives

    # catch-all regex for generic CLI, including following prompts:
    #   [root@vsh1 ~]#
    CLI_START_PROMPT = '(^|\n|\r)(\[?\S+\s?\S+\]?)(#|\$|>|~)(\s)?$'
    CLI_ANY_PROMPT = CLI_START_PROMPT

    def __init__(self, host, user='admin', password='', terminal='console',
                 transport_type='ssh', **channel_args):
        """
        Create a new Cli Channel object.

        :param host: host/ip
        :type host: string
        :param user: username to log in with
        :type user: string
        :param password: password to log in with
        :type password: string
        :param terminal:  terminal emulation to use; default to 'console'
        :type terminal: string
        :param transport_type: telnet or ssh, defaults to ssh
        :type transport_type: string
        :param channel_args: additional ``transport_type``-dependent
            arguments, passed blindly to the transport ``start`` method.
        :type channel_args: determined by the channel's constructor
            where appropriate.
        """

        self._host = host
        self._user = user
        self._password = password
        self._terminal = terminal
        self._transport_type = transport_type
        self._new_transport = False
        self._transport = None
        self._channel_args = channel_args
        self._log = logging.getLogger(__name__)

        self.channel = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        if self._new_transport and self._transport:
            self._transport.disconnect()
            self._transport = None

    def start(self, start_prompt=None):
        """
        Initialize underlying channel.

        :param start_prompt: A non-default prompt to match, if any.
        :type start_prompt: regex pattern
        """
        if self._transport_type == 'ssh':
            self._initialize_cli_over_ssh()
        elif self._transport_type == 'telnet':
            self._initialize_cli_over_telnet()
        elif self._transport_type == 'libvirt':
            self._initialize_cli_over_libvirt()
        else:
            raise NotImplementedError(
                "Unsupported transport type %s" % self._transport_type)

        # Wait for a prompt, try and figure out where we are.  It's a new
        # channel so we should only be at bash or the main CLI prompt.
        if start_prompt is None:
            start_prompt = self.CLI_START_PROMPT
        self.channel.start(start_prompt)

    def _initialize_cli_over_ssh(self):
        """
        Initialize underlying ssh transport and ssh channel. It expect ssh to
        shell or cli. Start cli if ssh-ed to shell.
        """

        # Create SSHProcess
        if self._transport is None:
            self._transport = SSHProcess(self._host,
                                         self._user,
                                         self._password)
            self._new_transport = True

        # Create ssh channel and start channel
        self.channel = SSHChannel(self._transport, self._terminal)

    def _initialize_cli_over_telnet(self):
        """
        Create and inititalize telnet channel. It assume telnet to either
        shell or cli. Start cli if telneted to shell.
        """
        # Create telnet channel
        self.channel = TelnetChannel(self._host, self._user, self._password)

    def _initialize_cli_over_libvirt(self):
        """
        Create and inititalize libvirt channel. Same general logic as telnet.
        """

        # Create libvirt channel.  self._channel_args should contain
        # a 'domain_name' argument.
        self.channel = LibVirtChannel(user=self._user,
                                      password=self._password,
                                      **self._channel_args)

    def _send_and_wait(self, text_to_send, match_res, timeout=60):
        """
        Discard old data in buffer, sends data, then blocks until some text is
        received that matches one or more patterns.

        :param text_to_send: Text to send, may be empty.  Note, you are
                             responsible for your own command terminator!
        :param match_res: Pattern(s) to look for to be considered successful.
        :param timeout: Maximum time, in seconds, to wait for a regular
                        expression match. 0 to wait forever.

        :return: (output, re.MatchObject) where output is the output of the
                 command (without the matched text), and MatchObject is
                 a Python re.MatchObject containing data on what was matched.
        """
        # TODO: There was a call to 'self.channel.receive_all()' here, which
        # appears to be used to 'flush' the buffer first.  For interactive
        # prompts on libvirtchannel, this was causing an endless blocking call.
        # We still probably want to figure out an alternative.
        self.channel.send(text_to_send)
        return self.channel.expect(match_res, timeout)

    def _send_line_and_wait(self, text_to_send, match_res, timeout=60):
        """
        Same to _send_and_wait but automatically append a newline to data
        before send.

        :param text_to_send: Text to send, may be empty.  Note, you are
                             responsible for your own command terminator!
        :param match_res: Pattern(s) to look for to be considered successful.
        :param timeout: Maximum time, in seconds, to wait for a regular
                        expression match. 0 to wait forever.

        :return: (output, re.MatchObject) where output is the output of the
                 command (without the matched text), and MatchObject is
                 a Python re.MatchObject containing data on what was matched.
        """
        text_to_send = text_to_send + ENTER_LINE
        return self._send_and_wait(text_to_send, match_res, timeout)

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
                                                   self.CLI_ANY_PROMPT,
                                                   timeout=timeout)

        # CLI adds on escape chars and such sometimes (see bug 75081), so to
        # remove the command we just send from the output, split the output
        # into lines, then rejoin it with the first line removed.
        output = '\n'.join(output.splitlines()[1:])

        if ((output_expected is not None) and (bool(output) !=
                                               bool(output_expected))):
            raise exceptions.UnexpectedOutput(command=command,
                                              output=output,
                                              expected_output=output_expected)
        return output
