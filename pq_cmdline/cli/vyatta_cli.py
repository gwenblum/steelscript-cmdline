# Copyright 2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.
from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import re

from pq_cmdline import exceptions
from pq_cmdline.cli import CLI, CLIMode


class VyattaCli(CLI):

    """
    Provides an interface to interact with the CLI of a vyatta router
    """

    # Vyatta prompts are of the following format:
    # 'user vyatta' login : "vyatta@vyatta6:~$"
    # this might change later on

    NAME_PREFIX_RE = '(?P<user>[a-zA-Z][a-zA-Z0-9_\-]*)'
    NAME_PREFIX_RE += '@(?P<name>[a-zA-Z0-9_\-.]+)'

    # Vyatta prompt terminator is as follows
    # For 'root' users:
    # * normal mode: "root@vyatta6:~# "
    # * config mode: "root@vyatta6# "
    #
    # For 'vyatta', non root users:
    # * normal mode: "vyatta@vyatta6:~$ "
    # * config mode: "vyatta@vyatta6#"

    CLI_NORMAL_PROMPT = NAME_PREFIX_RE + ':~[\$|#]'
    CLI_CONFIG_PROMPT = NAME_PREFIX_RE + '#'
    CLI_ANY_PROMPT = [CLI_NORMAL_PROMPT, CLI_CONFIG_PROMPT]

    # CLI_START_PROMPT is needed by base CLI class for the first
    # prompt expected on login to device. Either telnet or ssh.
    CLI_START_PROMPT = CLI_NORMAL_PROMPT

    # add error prompts to this variable
    CLI_ERROR_PROMPT = '^Cannot'

    # Line to be discarded from CLI output
    DISCARD_PROMPT = '[edit]'

    def start(self):
        """
        Initialize underlying channel.

        Vyatta transport channel is presently configured to SSH only.
        There is no limitation for this, Vyatta could be configured
        for telnet as well, but that would involve additional config
        on Vyatta bring up during install. Ignoring for now.
        """
        if self._transport_type == 'ssh':
            self._initialize_cli_over_ssh()
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
        self._log.debug('Disabling paging on Vyatta')
        self._send_line_and_wait(
            'set terminal length 0',
            self.CLI_NORMAL_PROMPT)

    def current_cli_mode(self):
        """
        Determine what mode the CLI is at. This is done by sending newline on
        the channel and check which prompt pattern matches.

        :return: current CLI mode.
        :raises UnknownCLIMode: if the current mode could not be detected.
        """

        (output, match) = self._send_line_and_wait('',
                                                   [self.CLI_NORMAL_PROMPT,
                                                    self.CLI_CONFIG_PROMPT, ])

        modes = {self.CLI_NORMAL_PROMPT: CLIMode.NORMAL,
                 self.CLI_CONFIG_PROMPT: CLIMode.CONFIG, }

        if match.re.pattern not in modes:
            raise exceptions.UnknownCLIMode(prompt=output)
        return modes[match.re.pattern]

    def enter_mode(self, mode=CLIMode.CONFIG, force=False):
        """
        Enter the mode based on mode string ('normal','config').

        :param mode: The CLI mode to enter. It must be 'normal', 'enable', or
                   'configure'
        :type mode: string

        :param force: Discard commits and force enter requested mode
        :type force: Boolean

        :raises UnknownCLIMode: if mode is not "normal", "configure"
        """
        if mode == CLIMode.NORMAL:
            self.enter_mode_normal(force)

        elif mode == CLIMode.CONFIG:
            self.enter_mode_config()

        else:
            raise exceptions.UnknownCLIMode(mode=mode)

    def enter_mode_normal(self, force=False):
        """
        Puts the CLI into the 'normal' mode. In this mode you can run commands,
        but you cannot change the configurations.

        :param force: Will force enter 'normal' mode, discarding all changes
                     that haven't been committed.
        :type force: Boolean

        :raises CLIError: if unable to go from "configure" mode to "normal"
                          This happens if "commit" is not applied after config
                          changes
        :raises UnknownCLIMode: if mode is not "normal" or "configure"
        """

        self._log.info('Going to normal mode')
        mode = self.current_cli_mode()

        if mode == CLIMode.NORMAL:
            self._log.debug('Already at normal, doing nothing')

        elif mode == CLIMode.CONFIG:
            if force:
                self._log.debug('Entering normal mode, discarding all commits')
                self._send_line_and_wait(
                    'exit discard',
                    self.CLI_NORMAL_PROMPT)

            else:
                self._log.debug('Entering normal mode')
                (output, match_res) = self._send_line_and_wait(
                    'exit', [self.CLI_ERROR_PROMPT, self.CLI_NORMAL_PROMPT])

                if re.match(self.CLI_ERROR_PROMPT, match_res.string):
                    raise exceptions.CLIError(
                        command="exit", output=match_res.string, mode=mode)
        else:
            raise exceptions.UnknownCLIMode(mode=mode)

    def enter_mode_config(self):
        """
        Puts the CLI into config mode, if it is not there already. In this
        mode, you can make changes in configurations.

        :raises UnknownCLIMode: if mode is not "normal", "configure"
        """

        self._log.debug('Going to Config mode')

        mode = self.current_cli_mode()

        if mode == CLIMode.NORMAL:
            self._send_line_and_wait('configure', self.CLI_CONFIG_PROMPT)
        elif mode == CLIMode.CONFIG:
            self._log.debug('Already at Config, doing nothing')
        else:
            raise exceptions.UnknownCLIMode(mode=mode)

    def exec_command(self, command, timeout=60, mode=CLIMode.CONFIG,
                     force=False, output_expected=None):
        """
        Executes the given command.

        This method handles detecting simple boolean conditions such as
        the presence of output or errors.

        :param command:  command to execute, newline appended automatically
        :param timeout:  maximum time, in seconds, to wait for the command to
            finish. 0 to wait forever.
        :param mode:  mode to enter before running the command.  To skip this
            step and execute directly in the cli's current mode, explicitly
            set this parameter to None.  The default is "configure"
        :param force: Will force enter mode, discarding all changes
                     that haven't been committed.
        :type force: Boolean
        :param output_expected: If not None, indicates whether output is
            expected (True) or no output is expected (False).
            If the oppossite occurs, raise UnexpectedOutput. Default is None.
        :type output_expected: bool or None

        :raises TypeError: if output_expected type is incorrect
        :raises CmdlineTimeout: on timeout
        :raises UnexpectedOutput: if output occurrs when no output was
            expected, or no output occurs when output was expected

        :return: output of the command, minus the command itself.
        """
        if output_expected is not None and not isinstance(
                output_expected, bool):
            raise TypeError("exec_command: output_expected requires a boolean "
                            "value or None")
        if mode is not None:
            self.enter_mode(mode, force)

        self._log.debug('Executing cmd "%s"' % command)

        (output, match_res) = self._send_line_and_wait(command,
                                                       self.CLI_ANY_PROMPT,
                                                       timeout=timeout)
        output = output.splitlines()[1:]

        # Vyatta does not have a standard error prompt
        # In config mode, each command (errorneous or not) is
        # followed with '[edit]'. This skews the result for
        # output_expected flag

        # To address this remove line with '[edit]' when in config mode

        if mode == CLIMode.CONFIG:
            output = [line for line in output if self.DISCARD_PROMPT != line]

        output = '\n'.join(output)

        if ((output_expected is not None) and (bool(output) !=
                                               bool(output_expected))):
            raise exceptions.UnexpectedOutput(command=command,
                                              output=output,
                                              expected_output=output_expected)
        return output
