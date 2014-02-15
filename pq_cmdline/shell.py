# Copyright 2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import sys
import paramiko
import logging
import time
import select

from pq_runtime.exceptions import (re_raise, SshError, CommandError,
                                   CommandTimeout, NbtError)
from pq_cmdline.sshprocess import SshProcess


class Shell(object):
    """
    Class for running shell command remotely. It runs commands stateless.
    No persistent channel is maintained.
    So an exec_command cannot use environment variables/directory
    changes/whatever from a previous command execution.
    """

    def __init__(self, host, user='root', password=''):
        """
        Create a Shell object to 'host' with specified user and password.
        Automatically connect underlying transport if it is not connected.

        :param host: host/ip to ssh into
        :param user: username to log in with
        :param password: password to log in with
        """

        ## Hostname shell connects to
        self._host = host

        ## Username shell connects with
        self._user = user

        ## Password shell connects with
        self._password = password

        # Initialize underlying sshprocess, which
        # http://www.lag.net/paramiko/docs/
        self.sshprocess = SshProcess(host=host, user=user, password=password)
        self.sshprocess.connect()

        ## Logging module
        self._log = logging.getLogger(__name__)

    def exec_command(self, command, timeout=60):
        """
        Executes the given command.  Note, this is stateless.
        So an exec_command cannot use environment variables/directory
        changes/whatever from a previous exec_command.

        :param command: command to send
        :param timeout: seconds to wait for command to finish. None to disable

        :raises SshError: if not connected
        :raises CommandTimeout: on timeout

        :return: (output, exit_code) for the command.
        """

        self._log.debug('Executing command "%s"' % command)

        # connect if ssh is not connected
        if (not self.sshprocess.is_connected()):
            self.sshprocess.connect()

        channel = self.sshprocess.transport.open_session()

        # Put stderr into the same output as stdout.
        channel.set_combine_stderr(True)

        starttime = time.time()

        # XXX/tsinclair  Paramiko 1.7.5 has a bug in its internal event system
        # that can cause it to sometimes throw a 'not connected' exception when
        # running exec_command.  If we get that exception here, but we're still
        # connected, then just eat the exception and go on, since that's the
        # normal case.  This will hopefully be fixed in 1.7.6 and this
        # try/except removed.
        try:
            channel.exec_command(command)
        except paramiko.SSHException:
            if not self.sshprocess.is_connected():
                re_raise(SshError, "Not connected to %s" % self._host)
            else:
                self._log.debug(
                    'Ignore Paramiko SSHException due to 1.7.5 bug')

        chan_closed = False
        output = ""

        # Read until we time out or the channel closes
        while not chan_closed:

            # Use select to check whether channel is ready for read.
            # Reading on the channel directly would block until data is
            # ready, where select blocks at most 10 seconds which allows
            # us to check whether the specified timeout has been reached.
            # If channel is not ready for reading within 10 seconds,
            # select returns an empty list to 'readers'.
            (readers, w, x) = select.select([channel], [], [], 10)

            # Timeout if this is taking too long.
            if timeout and ((time.time() - starttime) > timeout):
                raise CommandTimeout('Command "%s" timed out after %d seconds'
                                     % (command, timeout))

            # If the reader-ready list isn't empty, then read.  We know it must
            # be channel here, since thats all we're waiting on.
            if len(readers) > 0:
                data = channel.recv(4096)

                # If we get no data back, the channel has closed.
                if len(data) > 0:
                    output += data
                else:
                    chan_closed = True

            elif channel.exit_status_ready():
                # XXX/tsinclair - I don't fully understand what's going on, but
                # this seems to work.  If no readers were available, see if the
                # exit status is ready - if so, the channel must be closed.
                # exit_status_ready can return true before we've read all the
                # data.  Problem is, I know I've seen it return true when there
                # was no data, and then data came in afterwards, so this might
                # occassionally trip early.  If only paramiko.channel had a way
                # to see if it was closed..
                chan_closed = True

        # Done reading.  Now we need to wait for the exit status/channel close.
        # Rather than block here, we'll poll to ensure we don't get stuck.
        while not channel.exit_status_ready():
            if timeout and ((time.time() - starttime) > timeout):
                raise CommandTimeout('Command "%s" timed out after %d seconds'
                                     % (command, timeout))
            else:
                time.sleep(0.5)

        exit_status = channel.recv_exit_status()
        channel.close()

        # If the command failed and the user wants an exception, do it!
        if (exit_status != 0) and except_on_error:
            raise CommandError('Command "%s" returned %d with the output:\n%s'
                               % (command, exit_status, output))

        return (output, exit_status)
