# $Id$
#
# Copyright 2013 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import absolute_import

import logging
import re

from pq_runtime.exceptions import CommandError, CommandTimeout
from pq_cmdline.interactive_channel import InteractiveChannel


class CLILevel(object):
    """
    Different config levels the CLI can be in, plus one if it's not even in the
    CLI for some reason (ie back to bash).  These need to be in order!
    """
    bash = 0
    root = 1
    enable = 2
    config = 3


class Cli(object):
    """
    Provides an interface to interact with the command-line interface (CLI) of
    a Riverbed appliance.
    """

    cli_exec_path = '/opt/tms/bin/cli'

    # Sends control-c, causes CLI to cancel the current command
    text_control_c = '\x03'

    # Control-u clears any entered text.  Neat.
    text_prompt_clear = '\x15'

    # Regexes for the different prompts.  Prompt start is hard - sometimes
    # there are ansi escape codes at the start, can't get them to shut off.
    name_prefix_re = '^(\x1b\[[a-zA-Z0-9]+)?(?P<name>[a-zA-Z0-9_\-.:]+)'

    cli_root_prompt = name_prefix_re + ' >'
    cli_enable_prompt = name_prefix_re + ' #'
    cli_conf_prompt = name_prefix_re + ' \(config\) #'
    prompt_cli_any = name_prefix_re + ' (>|#|\(config\) #)'

    # Matches the prompt used by less
    prompt_less = '(^|\n|\r)lines \d+-\d+'

    def __init__(self, interactive_channel):
        """
        Create a new Cli Channel object.

        :param interactive_channel: the interactive channel used by cli
        """
        self.channel = interactive_channel
        self.log = logging.getLogger('%s/%s' % (self.__class__.__name__,
                                                self.channel.hostname))

    def start(self, terminal='console', exec_path=None, timeout=60):
        """
        Starts the interactive shell session.

        :param terminal:  terminal emulation to use
        :param exec_path:  custom path to the CLI executable to use,
                           None for the default
        :param timeout:  max time, in seconds, to wait for the CLI prompt
                         before giving up

        :raises CommandTimeout: if the prompt is not seen before timeout seconds
        :raises CommandError: if exec_path is set, but the channel did not start
                              at the bash prompt (ie, we do not have shell access)
        """

        # Open up the channel
        self.channel.start(terminal)

        # Wait for a prompt, try and figure out where we are.  It's a new
        # channel so we should only be at bash or the main CLI prompt.
        (output, match) = self.channel.wait_for_prompt(
            [self.channel.bash_prompt, self.cli_root_prompt])

        if match.re.pattern == self.channel.bash_prompt:
            self.log.info('At bash prompt, executing CLI')
            (output, match) = self.channel.send_and_wait(
                (exec_path or self.cli_exec_path) + '\n',
                self.cli_root_prompt,
                timeout)
        elif exec_path and (exec_path != self.cli_exec_path):
            raise CommandError('Started at CLI, not BASH - could not execute '
                               'custom CLI exec_path "%s"' % exec_path)

        # Disable session paging. When we run a CLI command, we want to get
        # all output instead of a page at a time.
        self.log.info('Disabling paging')
        (output, match) = self.channel.send_and_wait(
            'no cli session paging enable\n', self.cli_root_prompt)

    def stop(self):
        """
        Stop the interactive shell session.
        """
        self.channel.stop()

    def current_cli_level(self):
        """
        Determine what level the CLI is at. This is done by sending newline on the
        channel and check which prompt pattern matches.

        :return: current CLI level. Throws exceptions if current CLI level
                 could not be detected.
        """

        (output, match) = self.channel.send_and_wait(
            '\n', [self.channel.bash_prompt, self.cli_root_prompt,
                   self.cli_enable_prompt, self.cli_conf_prompt])

        levels = {self.channel.bash_prompt: CLILevel.bash,
                  self.cli_root_prompt: CLILevel.root,
                  self.cli_enable_prompt: CLILevel.enable,
                  self.cli_conf_prompt: CLILevel.config}

        return levels[match.re.pattern]

    def enter_mode(self, mode="configure"):
        """
        Enter mode based on mode string ('normal', 'enable', or 'configure').

        :param mode: The CLI mode to enter. It must be 'normal', 'enable', or
                   'configure'

        :raises NotImplementedError: if mode is not "normal", "enable", or
                                     "configure"
        :raises CommandError: if the shell is not in the CLI.
        """
        if mode == "normal":
            self.enter_level_root()

        elif mode == "enable":
            self.enter_level_enable()

        elif mode == "configure":
            self.enter_level_config()

        else:
            raise NotImplementedError("unknown mode: %s" % mode)

    def enter_level_root(self):
        """
        Puts the CLI into the 'root' mode (where it is when the CLI first
        executes), if it is not there already.  Note this will go 'backwards'
        if needed (e.g., exiting config mode)

        :raises CommandError: if the shell is not in the CLI; current thinking
                              is this indicates the CLI has crashed/exited, and
                              it is better to open a new CliChannel than have
                              this one log back in and potentially hide an
                              error.
        """

        self.log.info('Going to root level')

        self.channel.verify_connected()

        level = self.current_cli_level()

        if level == CLILevel.bash:
            raise CommandError('Channel is at the Bash prompt; CLI crashed?')

        elif level == CLILevel.root:
            self.log.debug('Already at root, doing nothing')

        elif level == CLILevel.enable:
            self.channel.send_and_wait('disable\n', self.cli_root_prompt)

        elif level == CLILevel.config:
            self.channel.send_and_wait('exit\n', self.cli_enable_prompt)
            self.channel.send_and_wait('disable\n', self.cli_root_prompt)

        else:
            raise CommandError('Unknown CLI level')

    def enter_level_enable(self):
        """
        Puts the CLI into enable mode, if it is not there already.  Note this
        will go 'backwards' if needed (e.g., exiting config mode)

        :raises CommandError: if the shell is not in the CLI; current
                              thinking is this indicates the CLI has
                              crashed/exited, and it is better to open a
                              new CliChannel than have this one log back in
                              and potentially hide an error.
        """

        self.log.info('Going to Enable level')

        self.channel.verify_connected()

        level = self.current_cli_level()

        if level == CLILevel.bash:
            raise CommandError('Channel is at the Bash prompt; CLI crashed?')

        elif level == CLILevel.root:
            self.channel.send_and_wait('enable\n', self.cli_enable_prompt)

        elif level == CLILevel.enable:
            self.log.debug('Already at Enable, doing nothing')

        elif level == CLILevel.config:
            self.channel.send_and_wait('exit\n', self.cli_enable_prompt)

        else:
            raise CommandError('Unknown CLI level')

    def enter_level_config(self):
        """
        Puts the CLI into config mode, if it is not there already.

        :raises CommandError: if the shell is not in the CLI; current thinking
                              is this indicates the CLI has crashed/exited, and
                              it is better to open a new CliChannel than have
                              this one log back in and potentially hide an
                              error.
        """

        self.log.info('Going to Config level')

        self.channel.verify_connected()

        level = self.current_cli_level()

        if level == CLILevel.bash:
            raise CommandError('Channel is at the Bash prompt; CLI crashed?')

        elif level == CLILevel.root:
            self.channel.send_and_wait('enable\n', self.cli_enable_prompt)
            self.channel.send_and_wait('config terminal\n',
                                       self.cli_conf_prompt)

        elif level == CLILevel.enable:
            self.channel.send_and_wait('config terminal\n',
                                       self.cli_conf_prompt)

        elif level == CLILevel.config:
            self.log.info('Already at Config, doing nothing')

        else:
            raise CommandError('Unknown CLI level')

    def run_command(self, command, except_on_error=True, timeout=60,
                    quiet=False):
        """
        Runs the given command - newline is appended automatically

        :param command:  command to execute, newline appended automatically
        :param except_on_error:  if True, CommandError will be raised if the
                                 CLI returns a string starting with %.
        :param timeout:  maximum time, in seconds, to wait for the command to
                         finish. 0 to wait forever.

        :param quiet:  don't log the command executed.

        :raises CommandTimeout: if the command did not complete before the
                                timeout expired.
        :raises CommandError: if the CLI returns a string starting with % and
                              except_on_error is True

        :return: the output of the command, minus the command itself.
        """

        if not quiet:
            self.log.info('Executing cmd "%s"' % command)

        (output, match) = self.channel.send_and_wait(
            command + '\n', self.prompt_cli_any, timeout=timeout)

        # CLI adds on escape chars and such sometimes (see bug 75081), so to
        # remove the command we just send from the output, split the output
        # into lines, then rejoin it with the first line removed.
        output = '\n'.join(output.splitlines()[1:])

        if except_on_error and output and (output[0] == '%'):
            raise CommandError('CLI error from command "%s":\n%s'
                               % (command, output))

        return output

    def run_and_validate(self, command, expected_output, timeout=60):
        """
        Runs the given command (newline is appended automatically), verifying that
        expected_output is present in the output returned by the CLI.

        :param command: command to execute, newline appended automatically
        :param expected_output:  a string, interpreted as a regex. If it is
                                 None or empty, we expect the output returned
                                 for the command to be empty too. Otherwise,
                                 we expect a subset of the output matches the
                                 expected_output.
        :param timeout:  maximum time, in seconds, to wait for the command to
                         finish. 0 to wait forever.

        :raises CommandError: if the expected output is not present
        :raises CommandTimeout: if the command did not complete before the
                                timeout expired.

        :return: the output of the command, minus the command itself.
        """

        # Don't throw an exception on error here, since we're looking for a
        # specific string; the string probably won't be found on error.
        output = self.run_command(command, timeout=timeout,
                                  except_on_error=False)

        # If the expected_output is an empty string/None/etc, don't use it as
        # a regex as it'll match anything.
        if not expected_output:
            match = (len(output) == 0)

        else:
            match = re.search(expected_output, output)

        if not match:
            raise CommandError(
                'Command "%s" did not return expected output:\n%s\n\n'
                'Output was:\n%s' % (command, expected_output, output))

        return output
