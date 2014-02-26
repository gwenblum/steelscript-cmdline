# Copyright 2013 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import logging

from pq_cmdline.ssh_channel import SSHChannel
from pq_cmdline.sshprocess import SSHProcess
from pq_cmdline.telnet_channel import TelnetChannel
from pq_cmdline import exceptions

# Control-u clears any entered text.  Neat.
DELETE_LINE = b'\x15'

# Command terminator
ENTER_LINE = b'\r'


class CLIMode(object):
    """
    Different config modes the CLI can be in, plus one if it's not even in the
    CLI for some reason (ie back to bash).
    """
    BASH = 'bash'
    NORMAL = 'normal'
    ENABLE = 'enable'
    CONFIG = 'configure'


class CLI(object):
    """
    New implementation of CLI for a Riverbed appliance.
    """

    CLI_EXEC_PATH = '/opt/tms/bin/cli'

    # Regexes for the different prompts.  Prompt start is hard - sometimes
    # there are ansi escape codes at the start, can't get them to shut off.
    NAME_PREFIX_RE =\
        '(^|\n|\r)(\x1b\[[a-zA-Z0-9]+)?(?P<name>[a-zA-Z0-9_\-.:]+)'

    CLI_NORMAL_PROMPT = NAME_PREFIX_RE + ' >'
    CLI_ENABLE_PROMPT = NAME_PREFIX_RE + ' #'
    CLI_CONF_PROMPT = NAME_PREFIX_RE + ' \(config\) #'
    CLI_ANY_PROMPT = NAME_PREFIX_RE + ' (>|#|\(config\) #)'

    # Matches the prompt used by less
    prompt_less = '(^|\n|\r)lines \d+-\d+'

    def __init__(self, host, user='admin', password='', terminal='console',
                 transport_type='ssh'):
        """
        Create a new Cli Channel object.

        :param host: host/ip
        :param user: username to log in with
        :param password: password to log in with
        :param terminal:  terminal emulation to use; default to 'console'
        """

        self._host = host
        self._user = user
        self._password = password
        self._terminal = terminal
        self._transport_type = transport_type
        self._new_transport = False
        self._transport = None
        self._log = logging.getLogger(__name__)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        if self._new_transport and self._transport:
            self._transport.disconnect()
            self._transport = None

    def start(self):
        """
        Initialize underlying channel.
        """
        if self._transport_type == 'ssh':
            self._initialize_cli_over_ssh()
        elif self._transport_type == 'telnet':
            self._initialize_cli_over_telnet()
        else:
            raise NotImplementedError(
                "Unsupported transport type %s" % self._transport_type)

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

        # Wait for a prompt, try and figure out where we are.  It's a new
        # channel so we should only be at bash or the main CLI prompt.
        (output, match) = self.channel.expect([self.channel.BASH_PROMPT,
                                               self.CLI_NORMAL_PROMPT])

        # Start cli if log into shell
        timeout = 60
        if match.re.pattern == self.channel.BASH_PROMPT:
            self._log.info('At bash prompt, executing CLI')
            self._send_line_and_wait(self.CLI_EXEC_PATH,
                                     [self.CLI_NORMAL_PROMPT], timeout)
        self._disable_paging()

    def _disable_paging(self):
        """
        Disable session paging. When we run a CLI command, we want to get
        all output instead of a page at a time.
        """
        self._log.info('Disabling paging')
        self._send_line_and_wait('no cli session paging enable',
                                 [self.CLI_NORMAL_PROMPT])

    def _initialize_cli_over_telnet(self):
        """
        Create and inititalize telnet channel. It assume telnet to either
        shell or cli. Start cli if telneted to shell.
        """

        # Create telnet channel
        self.channel = TelnetChannel(self._host, self._user, self._password)

        # Start and Wait for a prompt, try and figure out where we are.
        match = self.channel.start([self.channel.BASH_PROMPT,
                                    self.CLI_NORMAL_PROMPT])

        # Start cli if log into shell
        timeout = 60
        if match.re.pattern == self.channel.BASH_PROMPT:
            self._log.info('At bash prompt, executing CLI')
            self._send_line_and_wait(self.CLI_EXEC_PATH,
                                     [self.CLI_NORMAL_PROMPT], timeout)
        self._disable_paging()

    def _send_and_wait(self, text_to_send, match_res, timeout=60):
        """
        Discard old data in buffer, sends data, then blocks until some text is
        received that matches one or more patterns.

        :param text_to_send: Text to send, may be empty.  Note, you are
                             responsible for your own command terminator!
        :param match_text: Pattern(s) to look for to be considered successful.
        :param timeout: Maximum time, in seconds, to wait for a regular
                        expression match. 0 to wait forever.

        :return: (output, re.MatchObject) where output is the output of the
                 command (without the matched text), and MatchObject is
                 a Python re.MatchObject containing data on what was matched.
        """
        self.channel.receive_all()
        self.channel.send(text_to_send)
        return self.channel.expect(match_res, timeout)

    def _send_line_and_wait(self, text_to_send, match_res, timeout=60):
        """
        Same to _send_and_wait but automatically append a newline to data
        before send.

        :param text_to_send: Text to send, may be empty.  Note, you are
                             responsible for your own command terminator!
        :param match_text: Pattern(s) to look for to be considered successful.
        :param timeout: Maximum time, in seconds, to wait for a regular
                        expression match. 0 to wait forever.

        :return: (output, re.MatchObject) where output is the output of the
                 command (without the matched text), and MatchObject is
                 a Python re.MatchObject containing data on what was matched.
        """
        text_to_send = text_to_send + ENTER_LINE
        return self._send_and_wait(text_to_send, match_res, timeout)

    def current_cli_mode(self):
        """
        Determine what mode the CLI is at. This is done by sending newline
        and check which prompt pattern matches.

        :return: current CLI mode.
        :raises UnknownCLIMode: if the current mode could not be detected.
        """

        (output, match) = self._send_line_and_wait('',
                                                   [self.channel.BASH_PROMPT,
                                                    self.CLI_NORMAL_PROMPT,
                                                    self.CLI_ENABLE_PROMPT,
                                                    self.CLI_CONF_PROMPT])

        modes = {self.channel.BASH_PROMPT: CLIMode.BASH,
                 self.CLI_NORMAL_PROMPT: CLIMode.NORMAL,
                 self.CLI_ENABLE_PROMPT: CLIMode.ENABLE,
                 self.CLI_CONF_PROMPT: CLIMode.CONFIG}

        if match.re.pattern not in modes:
            raise exceptions.UnknownCLIMode(prompt=output)
        return modes[match.re.pattern]

    def enter_mode(self, mode=CLIMode.CONFIG):
        """
        Enter mode based on mode string ('normal', 'enable', or 'configure').

        :param mode: The CLI mode to enter. It must be 'normal', 'enable', or
                   'configure'

        :raises UnknownCLIMode: if mode is not "normal", "enable", or
                                "configure"
        :raises CLINotRunning: if the shell is not in the CLI.
        """
        if mode == CLIMode.NORMAL:
            self.enter_mode_normal()

        elif mode == CLIMode.ENABLE:
            self.enter_mode_enable()

        elif mode == CLIMode.CONFIG:
            self.enter_mode_config()

        else:
            raise exceptions.UnknownCLIMode(mode=mode)

    def enter_mode_normal(self):
        """
        Puts the CLI into the 'normal' mode (where it is when the CLI first
        executes), if it is not there already.  Note this will go 'backwards'
        if needed (e.g., exiting config mode)

        :raises CLINotRunning: if the shell is not in the CLI; current thinking
                               is this indicates the CLI has crashed/exited,
                               and it is better to open a new CliChannel than
                               have this one log back in and potentially hide
                               an error.
        """

        self._log.info('Going to normal mode')

        mode = self.current_cli_mode()

        if mode == CLIMode.BASH:
            raise exceptions.CLINotRunning()

        elif mode == CLIMode.NORMAL:
            self._log.debug('Already at normal, doing nothing')

        elif mode == CLIMode.ENABLE:
            self._send_line_and_wait('disable', self.CLI_NORMAL_PROMPT)

        elif mode == CLIMode.CONFIG:
            self._send_line_and_wait('exit', self.CLI_ENABLE_PROMPT)
            self._send_line_and_wait('disable', self.CLI_NORMAL_PROMPT)

    def enter_mode_enable(self):
        """
        Puts the CLI into enable mode, if it is not there already.  Note this
        will go 'backwards' if needed (e.g., exiting config mode)

        :raises CLINotRunning: if the shell is not in the CLI; current thinking
                               is this indicates the CLI has crashed/exited,
                               and it is better to open a new CliChannel than
                               have this one log back in and potentially hide
                               an error.
        """

        self._log.info('Going to Enable mode')

        mode = self.current_cli_mode()

        if mode == CLIMode.BASH:
            raise exceptions.CLINotRunning()

        elif mode == CLIMode.NORMAL:
            self._enable()

        elif mode == CLIMode.ENABLE:
            self._log.debug('Already at Enable, doing nothing')

        elif mode == CLIMode.CONFIG:
            self._send_line_and_wait('exit', self.CLI_ENABLE_PROMPT)

    def _enable(self):
        """
        Run cli command to enter enable mode. It may or may not require
        password.
        """
        password_prompt = '(P|p)assword:'
        (output, match) = self._send_line_and_wait('enable',
                                                   [self.CLI_ENABLE_PROMPT,
                                                    password_prompt])
        if match.re.pattern == password_prompt:
            self._send_line_and_wait(self._password, self.CLI_ENABLE_PROMPT)

    def enter_mode_config(self):
        """
        Puts the CLI into config mode, if it is not there already.

        :raises CLINotRunning: if the shell is not in the CLI; current thinking
                               is this indicates the CLI has crashed/exited,
                               and it is better to open a new CliChannel than
                               have this one log back in and potentially hide
                               an error.
        """

        self._log.info('Going to Config mode')

        mode = self.current_cli_mode()

        if mode == CLIMode.BASH:
            raise exceptions.CLINotRunning()

        elif mode == CLIMode.NORMAL:
            self._enable()
            self._send_line_and_wait('config terminal', self.CLI_CONF_PROMPT)

        elif mode == CLIMode.ENABLE:
            self._send_line_and_wait('config terminal', self.CLI_CONF_PROMPT)

        elif mode == CLIMode.CONFIG:
            self._log.info('Already at Config, doing nothing')

    def exec_command(self, command, timeout=60, mode='configure',
                     output_expected=None, error_expected=False):
        """Executes the given command.

        This method handles detecting simple boolean conditions such as
        the presence of output or errors.

        :param command:  command to execute, newline appended automatically
        :param timeout:  maximum time, in seconds, to wait for the command to
            finish. 0 to wait forever.
        :param mode:  mode to enter before running the command.  To skip this
            step and execute directly in the cli's current mode, explicitly
            set this parameter to None.  The default is "configure"
        :param output_expected: If not None, indicates whether output is
            expected (True) or no output is expected (False).
            If the oppossite occurs, raise UnexpectedOutput. Default is None.
        :type output_expected: bool or None
        :param error_expected: If true, cli error output (with a leading '%')
            is expected and will be returned as regular output instead of
            raising a CLIError.  Default is False, and error_expected always
            overrides output_expected.
        :type error_expected: bool

        :raises CmdlineTimeout: on timeout
        :raises CLIError: if the output matches the cli's error format, and
            error output was not expected.
        :raises UnexpectedOutput: if output occurrs when no output was
            expected, or no output occurs when output was expected

        :return: output of the command, minus the command itself.
        """

        if output_expected is not None and type(output_expected) is not bool:
            raise TypeError("exec_command: output_expected requires a boolean "
                            "value or None")

        if mode is not None:
            self.enter_mode(mode)

        self._log.debug('Executing cmd "%s"' % command)

        (output, match) = self._send_line_and_wait(command,
                                                   self.CLI_ANY_PROMPT,
                                                   timeout=timeout)

        # CLI adds on escape chars and such sometimes (see bug 75081), so to
        # remove the command we just send from the output, split the output
        # into lines, then rejoin it with the first line removed.
        output = '\n'.join(output.splitlines()[1:])

        if output and (output[0] == '%'):
            if error_expected:
                # Skip output_expected processing entirely.
                return output
            else:
                try:
                    mode = self.current_cli_mode()
                except exceptions.UnknownCLIMode:
                    mode = '<unrecognized>'
                raise exceptions.CLIError(command, output=output, mode=mode)

        if ((output_expected is not None) and (bool(output) !=
                                               bool(output_expected))):
            raise exceptions.UnexpectedOutput(command=command,
                                              output=output,
                                              expected_output=output_expected)
        return output

    def get_sub_commands(self, root_cmd):
        """
        Gets a list of commands at the current mode.  ie, it sends root_cmd
        with ? and returns everything that is a command. This strips out
        things in <>'s, or other free-form fields the user has to enter.

        :param root_cmd - root of the command to get subcommands for
        :return a list of the full paths to subcommands.  eg,  if root_cmd is
            "web ?", this returns ['web autologout', 'web auto-refresh', ...]
        """

        self._log.debug('Generating help for "%s"' % root_cmd)
        sub_commands = []
        output, match = self._send_and_wait('%s ?' % root_cmd,
                                            self.CLI_ANY_PROMPT)

        # Split the output into a list of lines. The first one will be the
        # command we sent, teh last two will be an escape code and the prompt,
        # So remove those.
        lines = output.splitlines()
        lines = lines[1:]

        self._log.info("raw output: %s" % lines)
        for line in lines:
            command = line.split(' ')[0]

            if command == '%':
                # Remove the command we enter to be back at the empty prompt
                self._send_line_and_wait(DELETE_LINE, self.CLI_ANY_PROMPT)
                try:
                    mode = self.current_cli_mode()
                except exceptions.UnknownCLIMode:
                    mode = '<unrecognized>'
                raise exceptions.CLIError(root_cmd, output=output, mode=mode)

            # If this is a user-input field, skip it. Most are surronded by
            # <>, but not all. If the command contains anything other than
            # letters or numbers, we assume it is a user field.
            if command.isalnum():
                if root_cmd:
                    sub_commands.append(root_cmd + ' ' + command)
                else:
                    sub_commands.append(command)

        # Remove the command we enter, so we're back at the empty prompt
        self._send_line_and_wait(DELETE_LINE, self.CLI_ANY_PROMPT)
        return sub_commands
