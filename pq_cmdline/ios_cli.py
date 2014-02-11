# Copyright 2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.
from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import logging
import re

from pq_runtime.exceptions import CommandError, CommandTimeout, NbtError
from pq_cmdline.cli import Cli2 as Cli


class IOSLevel(object):
    """
    Different config levels the CLI can be in, plus one if it's not even in the
    CLI for some reason (ie back to bash).  These need to be in order!
    """
    root = 1
    enable = 2
    config = 3
    subif = 4


class IosCli(Cli):
    """
    Provides an interface to interact with the command-line interface (CLI) of
    a IOS router
    """

    # Regexes for the different prompts.  Prompt start is hard - sometimes
    # there are ansi escape codes at the start, can't get them to shut off.
    # Presently all routers start with eiter tr or tsw
    name_prefix_re = '(^|\n|\r)(?P<name>t[a-zA-Z0-9_\-]+)'

    cli_root_prompt = name_prefix_re + '>'
    cli_enable_prompt = name_prefix_re + '#'
    cli_conf_prompt = name_prefix_re + '\(config\)#'
    cli_subif_prompt = name_prefix_re + '\(config-subif\)#'
    cli_any_prompt = name_prefix_re + '(>|#|\(config\)#|\(config-subif\)#)'

    # Matches the prompt used by less
    prompt_less = '(^|\n|\r)lines \d+-\d+'

    def _disable_paging(self):
        """
        Disable session paging. When we run a CLI command, we want to get
        all output instead of a page at a time.
        """
        self._log.info('Disabling paging')
        self._send_line_and_wait('terminal length 0',
                                 [self.cli_root_prompt])

    def current_cli_level(self):
        """
        Determine what level the CLI is at. This is done by sending newline on
        the channel and check which prompt pattern matches.

        :return: current CLI level. Throws exceptions if current CLI level
                 could not be detected.
        """

        (output, match) = self._send_line_and_wait('',
                                                   [self.cli_root_prompt,
                                                    self.cli_enable_prompt,
                                                    self.cli_conf_prompt,
                                                    self.cli_subif_prompt])

        levels = {self.cli_root_prompt: IOSLevel.root,
                  self.cli_enable_prompt: IOSLevel.enable,
                  self.cli_conf_prompt: IOSLevel.config,
                  self.cli_subif_prompt: IOSLevel.subif}

        return levels[match.re.pattern]

    def enter_level_subif(self, interface):
        """
        Puts the CLI into sub-interface mode, if it is not there already.

        :raises CommandError: if the shell is not in the CLI; current thinking
                              is this indicates the CLI has crashed/exited, and
                              it is better to open a new CliChannel than have
                              this one log back in and potentially hide an
                              error.
        """

        self._log.info('Going to sub-if level')

        level = self.current_cli_level()

        if level == IOSLevel.root:
            self._enable()
            self._send_line_and_wait('config terminal', self.cli_conf_prompt)
            self._send_line_and_wait("interface %s" % interface,
                                     self.cli_subif_prompt)
        elif level == IOSLevel.enable:
            self._send_line_and_wait('config terminal', self.cli_conf_prompt)
            self._send_line_and_wait("interface %s" % interface,
                                     self.cli_subif_prompt)
        elif level == IOSLevel.config:
            self._send_line_and_wait("interface %s" % interface,
                                     self.cli_subif_prompt)
        elif level == IOSLevel.subif:
            self._log.info("Already in sub-if level, exiting and re-entering")
            self._send_line_and_wait('exit', self.cli_conf_prompt)
            self._send_line_and_wait("interface %s" % interface,
                                     self.cli_subif_prompt)
        else:
            raise CommandError('Unknown CLI level')
