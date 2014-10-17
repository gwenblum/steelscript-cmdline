#!/usr/bin/python
# Copyright 2009-2013 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.
from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

from steelscript.common.app import Application
from steelscript.cmdline import cli


def filter(input_string, match=None, unmatch=None):
    """filter input_string on a per-line basis

    :param input_string: the input string to be filtered
    :param match: a string required in one line
    :param unmatch: a string should not exist in one line
    """
    ret = []
    for ln in input_string.split('\n'):
        if ((match is None or match in ln) and
                (unmatch is None or unmatch not in ln)):
            ret.append(ln)
    return '\n'.join(ret)


class BasicInfoCLI(cli.CLI):

    def disk_usage(self):
        """parse the output of 'df -h' and return a list of 3-element lists
        each list consist of mount point, use percentage and total size

        :param input_string: the output of df -h
        """
        output = filter(self.exec_command('df -h\n'), match='%',
                        unmatch='Filesystem')
        ret = []
        for ln in output.split('\n'):
            fs = ln.split()
            # fs follows pattern as "/dev/sda3 862G  183G  637G  23% /"
            # as "filesystem total used available percentage mount-point"
            ret.append(' '.join([fs[-1], fs[-5], fs[-2]]))
        return '\n'.join(ret)

    def time_info(self):
        """return time/timezone info by running 'date' command"""
        return self.exec_command('date\n')

    def cpu_load(self):
        """return the cpu load for the last minute, 5 minutes and 15 minutes"""
        return ' '.join(self.exec_command('uptime\n').split(' ')[-5:])


class BasicInfoApp(Application):

    def add_options(self, parser):
        super(BasicInfoApp, self).add_options(parser)

        parser.add_option('-H', '--host',
                          help='hostname or IP address')
        parser.add_option('-u', '--username', help="Username to connect with")
        parser.add_option('-p', '--password', help="Password to connect with")

    def validate_args(self):
        super(BasicInfoApp, self).validate_args()

        if not self.options.host:
            self.parser.error("Host name needs to be specified")

        if not self.options.username:
            self.parser.error("User Name needs to be specified")

        if not self.options.password:
            self.parser.error("Password needs to be specified")

    def main(self):
        with BasicInfoCLI(hostname=self.options.host,
                          username=self.options.username,
                          password=self.options.password) as cli:
            print (cli.time_info())
            print (cli.cpu_load())
            print (cli.disk_usage())


if __name__ == '__main__':
    BasicInfoApp().run()
