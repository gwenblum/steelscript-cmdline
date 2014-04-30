# Copyright 2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.
from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import re

from pq_cmdline import exceptions
from pq_cmdline.cli import CLIMode, CLI


class IOS_CLI(CLI):

    """
    Provides an interface to interact with the command-line interface (CLI) of
    a IOS router
    """

    # IOS are named as following:
    # tr2821-b or tsw27
    # oak-tr5 or oak-tsw5
    # 365-tr3 or 365-tsw27
    # and so forth

    NAME_PREFIX_RE = '(^|\n|\r)(?P<name>(\S+\-)?t[a-zA-Z0-9_\-]+)'

    CLI_NORMAL_PROMPT = NAME_PREFIX_RE + '>'
    CLI_ENABLE_PROMPT = NAME_PREFIX_RE + '#'
    CLI_CONFIG_PROMPT = NAME_PREFIX_RE + '\(config\)#'
    CLI_SUBIF_PROMPT = NAME_PREFIX_RE + '\(config-subif\)#'
    CLI_ANY_PROMPT = NAME_PREFIX_RE + '(>|#|\(config\)#|\(config-subif\)#)'

    # CLI_START_PROMPT is needed by base CLI class for the first
    # prompt expected on login to device. Either telnet or ssh.
    CLI_START_PROMPT = CLI_NORMAL_PROMPT
    CLI_ERROR_PROMPT = '(\s+)?(\^|%)'

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

        # Disable paging
        self._disable_paging()

    def _disable_paging(self):
        """
        Disable session paging. When we run a CLI command, we want to get
        all output instead of a page at a time.
        """
        self._log.debug('Disabling paging on IOS')
        self._send_line_and_wait('terminal length 0', self.CLI_NORMAL_PROMPT)

    def current_cli_mode(self):
        """
        Determine what mode the CLI is at. This is done by sending newline on
        the channel and check which prompt pattern matches.

        :return: current CLI mode.
        :raises UnknownCLIMode: if the current mode could not be detected.
        """

        (output, match_res) = self._send_line_and_wait('',
                                                       [self.CLI_NORMAL_PROMPT,
                                                        self.CLI_ENABLE_PROMPT,
                                                        self.CLI_CONFIG_PROMPT,
                                                        self.CLI_SUBIF_PROMPT])

        modes = {self.CLI_NORMAL_PROMPT: CLIMode.NORMAL,
                 self.CLI_ENABLE_PROMPT: CLIMode.ENABLE,
                 self.CLI_CONFIG_PROMPT: CLIMode.CONFIG,
                 self.CLI_SUBIF_PROMPT: CLIMode.SUBIF}

        if match_res.re.pattern not in modes:
            raise exceptions.UnknownCLIMode(prompt=output)
        return modes[match_res.re.pattern]

    def enter_mode(self, mode=CLIMode.CONFIG, interface=None):
        """
        Enter mode based on mode string ('normal', 'enable', or 'configure').

        :param mode: The CLI mode to enter. It must be 'normal', 'enable', or
                   'configure'
        :param interface: If entering sub-if mode, interface to enter

        :raises UnknownCLIMode: if mode is not "normal", "enable", or
                                "configure"
        """
        if mode == CLIMode.NORMAL:
            self.enter_mode_normal()

        elif mode == CLIMode.ENABLE:
            self.enter_mode_enable()

        elif mode == CLIMode.CONFIG:
            self.enter_mode_config()

        elif mode == CLIMode.SUBIF:
            self.enter_mode_subif(interface)

        else:
            raise exceptions.UnknownCLIMode(mode=mode)

    def enter_mode_normal(self):
        """
        Puts the CLI into the 'normal' mode (where it is when the CLI first
        executes), if it is not there already.  Note this will go 'backwards'
        if needed (e.g., exiting config mode)

        :raises UnknownCLIMode: if mode is not "normal", "enable", or
                                "configure"
        """

        self._log.debug('Going to normal mode')

        mode = self.current_cli_mode()

        if mode == CLIMode.NORMAL:
            self._log.debug('Already at normal, doing nothing')

        elif mode == CLIMode.ENABLE:
            self._send_line_and_wait('disable', self.CLI_NORMAL_PROMPT)

        elif mode == CLIMode.CONFIG:
            self._send_line_and_wait('end', self.CLI_ENABLE_PROMPT)
            self._send_line_and_wait('disable', self.CLI_NORMAL_PROMPT)

        elif mode == CLIMode.SUBIF:
            self._send_line_and_wait('end', self.CLI_ENABLE_PROMPT)
            self._send_line_and_wait('disable', self.CLI_NORMAL_PROMPT)

        else:
            raise exceptions.UnknownCLIMode(mode=mode)

    def enter_mode_enable(self):
        """
        Puts the CLI into enable mode, if it is not there already.  Note this
        will go 'backwards' if needed (e.g., exiting config mode)

        :raises UnknownCLIMode: if mode is not "normal", "enable", or
                                "configure"
        """

        self._log.debug('Going to Enable mode')

        mode = self.current_cli_mode()

        if mode == CLIMode.NORMAL:
            self._enable()

        elif mode == CLIMode.ENABLE:
            self._log.debug('Already at Enable, doing nothing')

        elif mode == CLIMode.CONFIG:
            self._send_line_and_wait('end', self.CLI_ENABLE_PROMPT)

        elif mode == CLIMode.SUBIF:
            self._send_line_and_wait('end', self.CLI_ENABLE_PROMPT)

        else:
            raise exceptions.UnknownCLIMode(mode=mode)

    def _enable(self):
        """
        Run cli command to enter enable mode. It may or may not require
        password.
        """
        password_prompt = '(P|p)assword:'
        (output, match_res) = self._send_line_and_wait('enable',
                                                       [self.CLI_ENABLE_PROMPT,
                                                        password_prompt])
        if match_res.re.pattern == password_prompt:
            self._send_line_and_wait(self._password, self.CLI_ENABLE_PROMPT)

    def enter_mode_config(self):
        """
        Puts the CLI into config mode, if it is not there already.

        :raises UnknownCLIMode: if mode is not "normal", "enable", or
                                "configure"
        """

        self._log.debug('Going to Config mode')

        mode = self.current_cli_mode()

        if mode == CLIMode.NORMAL:
            self._enable()
            self._send_line_and_wait('config terminal', self.CLI_CONFIG_PROMPT)

        elif mode == CLIMode.ENABLE:
            self._send_line_and_wait('config terminal', self.CLI_CONFIG_PROMPT)

        elif mode == CLIMode.CONFIG:
            self._log.debug('Already at Config, doing nothing')

        elif mode == CLIMode.SUBIF:
            self._send_line_and_wait('exit', self.CLI_CONFIG_PROMPT)

        else:
            raise exceptions.UnknownCLIMode(mode=mode)

    def enter_mode_subif(self, interface):
        """
        Puts the CLI into sub-interface mode, if it is not there already.
        """

        self._log.debug('Going to sub-if mode')
        if interface is None:
            raise ValueError('Cannot enter_mode_subif with Interface None')
        # enter mode config
        self.enter_mode(CLIMode.CONFIG)

        # enter sub-interface
        self._send_line_and_wait(
            "interface %s" %
            interface,
            self.CLI_SUBIF_PROMPT)

    def exec_command(self, command, timeout=60, mode=CLIMode.CONFIG,
                     output_expected=None, error_expected=False,
                     interface=None):
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
        :param interface: if mode 'subif', interface to configure 'gi0/1.666'
            or 'vlan 691'
        :type interface: string

        :raises CmdlineTimeout: on timeout
        :raises CLIError: if the output matches the cli's error format, and
            error output was not expected.
        :raises UnexpectedOutput: if output occurrs when no output was
            expected, or no output occurs when output was expected

        :return: output of the command, minus the command itself.
        """

        if output_expected is not None and not isinstance(
                output_expected, bool):
            raise TypeError("exec_command: output_expected requires a boolean "
                            "value or None")

        if mode is not None:
            self.enter_mode(mode, interface)

        self._log.debug('Executing cmd "%s"' % command)

        (output, match_res) = self._send_line_and_wait(command,
                                                       self.CLI_ANY_PROMPT,
                                                       timeout=timeout)

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
