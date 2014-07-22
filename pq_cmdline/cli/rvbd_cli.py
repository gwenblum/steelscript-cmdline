# -*- coding: utf-8 -*-

# Copyright 2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import re

from pq_cmdline import exceptions
from pq_cmdline.cli import CLIMode, CLI

# Control-u clears any entered text.  Neat.
DELETE_LINE = b'\x15'

# Command terminator
ENTER_LINE = b'\r'


class RVBD_CLI(CLI):

    """
    New implementation of CLI for a Riverbed appliance.
    """

    CLI_EXEC_PATH = '/opt/tms/bin/cli'

    # Regexes for the different prompts.  Prompt start is hard - sometimes
    # there are ansi escape codes at the start, can't get them to shut off.
    ANSI_PREFIX_RE = '(^|\n|\r)(\x1b\[[a-zA-Z0-9]+)?'
    NAME_PREFIX_RE = '%s(?P<name>[a-zA-Z0-9_\-.:]+)' % ANSI_PREFIX_RE

    CLI_SHELL_PROMPT = '(^|\n|\r)\[\S+ \S+\]#'

    # Amnesiac mode is how the CLI appears early on during installs.
    CLI_AMNESIAC_PROMPT = '%samnesiac#' % ANSI_PREFIX_RE
    CLI_NORMAL_PROMPT = NAME_PREFIX_RE + ' >'
    CLI_ENABLE_PROMPT = NAME_PREFIX_RE + ' #'
    CLI_CONF_PROMPT = NAME_PREFIX_RE + ' \(config\) #'
    CLI_ANY_PROMPT = NAME_PREFIX_RE + ' (>|#|\(config\) #)'

    # Matches the prompt used by less
    CLI_LESS_PROMPT = '(^|\n|\r)lines \d+-\d+'

    # CLI_START_PROMPT is needed by base CLI class for the first
    # prompt expected on login to device. Either telnet or ssh.
    CLI_START_PROMPT = [CLI_NORMAL_PROMPT, CLI_SHELL_PROMPT]
    CLI_ERROR_PROMPT = '^%'

    def start(self, start_prompt=None, run_cli=True):
        """
        Initialize the underlying channel, disable paging

        :param start_prompt: Allows overriding the standard initial
            match for any reasonable CLI prompt to expect a specific
            mode or handle an unusual situation such as the install wizard.
        :param run_cli: If True (the default), automatically launch
            the cli and disable paging.  This can be set to false
            to handle situations such as installation where the cli
            is launched differently.  The CLI will be running in normal mode.
        """
        super(RVBD_CLI, self).start(start_prompt=start_prompt)

        if run_cli:
            # Start cli if log into shell
            self._run_cli_from_shell()

            # Make sure we're in a known mode
            self.enter_mode_normal()

            # disable paging
            self._disable_paging()

    def _run_cli_from_shell(self):
        """
        Check to see if current mode is SHELL, start cli
        """
        mode = self.current_cli_mode()

        if mode == CLIMode.SHELL:
            timeout = 60
            self._log.debug('At bash prompt, executing CLI')
            self._send_line_and_wait(self.CLI_EXEC_PATH,
                                     [self.CLI_NORMAL_PROMPT], timeout)

    def _disable_paging(self):
        """
        Disable session paging. When we run a CLI command, we want to get
        all output instead of a page at a time.
        """
        self._log.debug('Disabling paging')
        self._send_line_and_wait('no cli session paging enable',
                                 [self.CLI_NORMAL_PROMPT])

    def current_cli_mode(self):
        """
        Determine what mode the CLI is at. This is done by sending newline
        and check which prompt pattern matches.

        :return: current CLI mode.
        :raises UnknownCLIMode: if the current mode could not be detected.
        """

        (output, match) = self._send_line_and_wait('',
                                                   [self.CLI_SHELL_PROMPT,
                                                    self.CLI_NORMAL_PROMPT,
                                                    self.CLI_ENABLE_PROMPT,
                                                    self.CLI_CONF_PROMPT])

        modes = {self.CLI_SHELL_PROMPT: CLIMode.SHELL,
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

        if mode == CLIMode.SHELL:
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

        if mode == CLIMode.SHELL:
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

        if mode == CLIMode.SHELL:
            raise exceptions.CLINotRunning()

        elif mode == CLIMode.NORMAL:
            self._enable()
            self._send_line_and_wait('config terminal', self.CLI_CONF_PROMPT)

        elif mode == CLIMode.ENABLE:
            self._send_line_and_wait('config terminal', self.CLI_CONF_PROMPT)

        elif mode == CLIMode.CONFIG:
            self._log.info('Already at Config, doing nothing')

    def exec_command(self, command, timeout=60, mode=CLIMode.CONFIG,
                     output_expected=None, error_expected=False, prompt=None):
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
            If the opposite occurs, raise UnexpectedOutput. Default is None.
        :type output_expected: bool or None
        :param error_expected: If true, cli error output (with a leading '%')
            is expected and will be returned as regular output instead of
            raising a CLIError.  Default is False, and error_expected always
            overrides output_expected.
        :type error_expected: bool
        :param prompt: Prompt regex for matching unusual prompts.  This should
            almost never be used as the ``mode`` parameter automatically
            handles all typical cases.  This parameter is for unusual
            situations like the install config wizard.

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

        if prompt is None:
            prompt = self._prompt
        (output, match_res) = self._send_line_and_wait(command,
                                                       prompt,
                                                       timeout=timeout)

        # CLI adds on escape chars and such sometimes (see bug 75081), and
        # the result is that some part of the command that was entered
        # shows up as an extra inital line of output.  Strip off that
        # initial line.
        output = '\n'.join(output.splitlines()[1:])

        if output and (re.match(self.CLI_ERROR_PROMPT, output)):
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
        output, match_res = self._send_and_wait('%s ?' % root_cmd,
                                                self.CLI_ANY_PROMPT)

        # Split the output into a list of lines. The first one will be the
        # command we sent, teh last two will be an escape code and the prompt,
        # So remove those.
        lines = output.splitlines()
        lines = lines[1:]

        self._log.debug("raw output: %s" % lines)
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
