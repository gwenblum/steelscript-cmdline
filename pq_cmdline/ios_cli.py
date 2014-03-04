# Copyright 2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.
from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import logging
import re

from pq_cmdline import exceptions
from pq_cmdline.cli import CLI


class IOSMode(object):
    """
    Different config modes the CLI can be in.
    """
    ROOT = 'root'
    ENABLE = 'enable'
    CONFIG = 'configure'
    SUBIF = 'subif'


class IOS_CLI(CLI):
    """
    Provides an interface to interact with the command-line interface (CLI) of
    a IOS router
    """

    # Regexes for the different prompts.  Prompt start is hard - sometimes
    # there are ansi escape codes at the start, can't get them to shut off.
    # Presently all routers start with eiter tr or tsw
    NAME_PREFIX_RE = '(^|\n|\r)(?P<name>t[a-zA-Z0-9_\-]+)'

    CLI_ROOT_PROMPT = NAME_PREFIX_RE + '>'
    CLI_ENABLE_PROMPT = NAME_PREFIX_RE + '#'
    CLI_CONF_PROMPT = NAME_PREFIX_RE + '\(config\)#'
    CLI_SUBIF_PROMPT = NAME_PREFIX_RE + '\(config-subif\)#'
    CLI_ANY_PROMPT = NAME_PREFIX_RE + '(>|#|\(config\)#|\(config-subif\)#)'

    # Matches the prompt used by less
    prompt_less = '(^|\n|\r)lines \d+-\d+'

    def _disable_paging(self):
        """
        Disable session paging. When we run a CLI command, we want to get
        all output instead of a page at a time.
        """
        self._log.info('Disabling paging')
        self._send_line_and_wait('terminal length 0',
                                 [self.CLI_ROOT_PROMPT])

    def current_cli_mode(self):
        """
        Determine what mode the CLI is at. This is done by sending newline on
        the channel and check which prompt pattern matches.

        :return: current CLI mode. Throws exceptions if current CLI mode
                 could not be detected.
        """

        (output, match) = self._send_line_and_wait('',
                                                   [self.CLI_ROOT_PROMPT,
                                                    self.CLI_ENABLE_PROMPT,
                                                    self.CLI_CONF_PROMPT,
                                                    self.CLI_SUBIF_PROMPT])

        modes = {self.CLI_ROOT_PROMPT: IOSMode.ROOT,
                 self.CLI_ENABLE_PROMPT: IOSMode.ENABLE,
                 self.CLI_CONF_PROMPT: IOSMode.CONFIG,
                 self.CLI_SUBIF_PROMPT: IOSMode.SUBIF}

        if match.re.pattern not in modes:
            raise exceptions.UnknownCLIMode(prompt=output)
        return modes[match.re.pattern]

    def enter_mode_subif(self, interface):
        """
        Puts the CLI into sub-interface mode, if it is not there already.

        :raises UnknownCLIMode: if the CLI is currently in
            an unrecognized mode.
        """

        self._log.info('Going to sub-if mode')

        mode = self.current_cli_mode()

        if mode == IOSMode.ROOT:
            self._enable()
            self._send_line_and_wait('config terminal', self.CLI_CONF_PROMPT)
            self._send_line_and_wait("interface %s" % interface,
                                     self.CLI_SUBIF_PROMPT)
        elif mode == IOSMode.ENABLE:
            self._send_line_and_wait('config terminal', self.CLI_CONF_PROMPT)
            self._send_line_and_wait("interface %s" % interface,
                                     self.CLI_SUBIF_PROMPT)
        elif mode == IOSMode.CONFIG:
            self._send_line_and_wait("interface %s" % interface,
                                     self.CLI_SUBIF_PROMPT)
        elif mode == IOSMode.SUBIF:
            self._log.info("Already in sub-if mode, exiting and re-entering")
            self._send_line_and_wait('exit', self.CLI_CONF_PROMPT)
            self._send_line_and_wait("interface %s" % interface,
                                     self.CLI_SUBIF_PROMPT)
