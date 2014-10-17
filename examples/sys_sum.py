#!/usr/bin/python
# Copyright 2009-2013 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.
from __future__ import print_function

import sys
import time
import logging

from steelscript.cmdline.sshprocess import SSHProcess

BYTES = 4096


class Appliance(object):
    """
    Generic appliance class

    :param host: hostname
    :param user: username
    :param pswd: password
    :param max_wait: maximum number of seconds of waiting
    """

    def __init__(self, host, user, pswd, max_wait):
        self._host = host
        self._user = user
        self._pswd = pswd
        self._max_wait = max_wait
        self._channel = None
        self._ssh = None

    def __enter__(self):
        self._ssh = SSHProcess(self._host, self._user, self._pswd)
        self._ssh._log.addHandler(logging.StreamHandler())
        self._ssh.connect()
        self._channel = self._ssh.open_interactive_channel()
        return self

    def request(self, cmd):
        self._channel.send(cmd)
        data = ''
        while not self._channel.recv_ready():
            time.sleep(1)
        data += self._channel.recv(BYTES)

        # in order to read the rest data from channel
        # wait till max_wait of seconds has reached
        # or there is data in the channel to read
        cnt = 0
        while cnt < self._max_wait and not self._channel.recv_ready():
            cnt += 1
            time.sleep(1)
        if self._channel.recv_ready():
            data += self._channel.recv(BYTES)
        return data

    def __exit__(self, type, value, traceback):
        self._channel.close()
        self._ssh.disconnect()


class LinuxBox(Appliance):

    @property
    def disk_usage(self):
        """parse the output of 'df -h' and return a list of 3-element lists
        each list consist of mount point, use percentage and total size

        :param input_string: the output of df -h
        """
        output = filter(self.request('df -h\n'), match=['%'],
                        unmatch=['Filesystem'])
        ret = []
        for ln in output.split('\n'):
            fs = ln.rstrip('\r').split()
            # fs follows pattern as "/dev/sda3 862G  183G  637G  23% /"
            # as "filesystem total used available percentage mount-point"
            ret.append(' '.join([fs[-1], fs[-5], fs[-2]]))
        return '\n'.join(ret)

    @property
    def time_info(self):
        """return time/timezone info by running 'date' command"""
        return filter(self.request('date\n'), match=[':'], unmatch=['Last'])

    @property
    def cpu_load(self):
        """return the cpu load for the last minute, 5 minutes and 15 minutes"""
        output = filter(self.request('uptime\n'), match=['load average'])
        return ' '.join(output.split(' ')[-5:])


def filter(input_string, match=None, unmatch=None):
    """filter input_string on a per-line baisis

    :param input_string: the input string to be filtered
    :param match: list of strings required in one line
    :param unmatch: list of strings should not exist in one line
    """
    return '\n'.join([ln for ln in input_string.split('\n')
                      if (not match or all(substr in ln for substr in match))
                      and (not unmatch or
                           not any(substr in ln for substr in unmatch))])


def usage():
    """print out expected arguments for the script"""
    print ("python sys_sum.py '<hostname>' "
           "'<username>'  '<password>'  <max_wait>\n"
           "hostname:  host name of the appliance \n"
           "username: user name to log into the appliance \n"
           "password: password to log into the appliance\n"
           "max_wait: maximum number of seconds for appliance to reply\n")


if __name__ == '__main__':
    args = sys.argv
    if len(args) == 2 and args[1] in ['-h', '--help']:
        usage()
    elif len(args) == 5:
        with LinuxBox(args[1], args[2], args[3], int(args[4])) as lb:
            print (lb.time_info)
            print ('CPU ' + lb.cpu_load)
            print (lb.disk_usage)
    else:
        usage()
