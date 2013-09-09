##
# $Id$
#
# Copyright 2013 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.
#
# Basic SSH shell, wrapped around Paramiko
# Modified based on codes from mgmt-fwk

import sys
import os
import paramiko
import logging
import time
import select

from nbt_exceptions import re_raise, SshError, CommandError, CommandTimeout
from zebra.interactive_channel import InteractiveChannel


class SshShell(object):
    """
    Wrapper class around paramiko.
    """

    def __init__(self, host, user='root', password=''):
        """
        Initializer

        @param host - host/ip to ssh into
        @param user - username to log in with
        @param password - password to log in with
        """

        ## Hostname shell connects to
        self.host = host

        ## Username shell connects with
        self.user = user

        ## Password shell connects with
        self.password = password

        ## paramiko.Transport object, the actual SSH engine.
        # http://www.lag.net/paramiko/docs/
        self.transport = None

        ## Logging module
        self.log = logging.getLogger(self.__class__.__name__)

    def __del__(self):
        """
        Deleter.  Ensure we're closed, just to be safe.
        """
        self.disconnect()

    def connect(self, timeout=5):
        """
        Starts up paramiko and connects to the host.

        @param timeout - an optional timeout (in seconds) for waiting for
                         ssh banner coming out. Defaults to 5 seconds.

        @exception SshCipherError on cipher mismatch
        @exception SshError on other error
        """
        self.log.info('Connecting to "%s" as "%s"' % (self.host, self.user))
        try:
            self.transport = paramiko.Transport((self.host, 22))
            self.transport.banner_timeout = timeout
            self.transport.start_client()
            self.transport.auth_password(self.user, self.password,
                                         fallback=False)
        except:
            # Close the session, or the child thread apparently hangs
            self.disconnect()
            re_raise(SshError, "Could not connect to %s" % self.host)

        # Quiet down paramiko's logger if our log level isn't set to debug.
        # It's annoying.

        if not self.log.isEnabledFor(logging.DEBUG):
            logger = logging.getLogger(self.transport.get_log_channel())
            logger.setLevel(logging.WARNING)

    def disconnect(self):
        """
        Disconnects from the host
        """

        if self.transport:
            self.transport.close()

    def exec_command(self, command, timeout=60, except_on_error=False):
        """
        Executes the given command.  This is a one-shot deal - no shell is
        running, so an exec_command cannot use environment variables/directory
        changes/whatever from a previous exec_command.

        @param command - command to send
        @param timeout - seconds to wait for command to finish. None to disable
        @param except_on_error - If True, throw a CommandError exception if
                               the command returns a non-zero return code

        @exception SshError if not connected
        @exception CommandError on non-zero return code from the command and
                   except_on_error is True
        @exception CommandTimeout on timeout

        @return (output, exit_code) for the command.
        """

        self.log.debug('Executing command "%s"' % command)

        # connect if ssh is not connected
        if (not self.transport) or (not self.transport.is_active()):
            self.connect()

        channel = self.transport.open_session()

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
            if not self.transport.is_active():
                raise
            else:
                self.log.debug('Ignore Paramiko SSHException due to 1.7.5 bug')

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

    def is_connected(self):
        """
        Check whether SSH connection is established or not.
        @Returns True if it is connected; returns False otherwise.
        """
        if self.transport and self.transport.is_active():
            return True
        return False

    def open_interactive_channel(self, term='console'):
        """
        Creates and starts an interactive channel that may be used to
        communicate with the remote end in a stateful way. This should be used
        over exec_command whenever the channel must remain open between
        commands for interactive processing, or when a terminal/tty is
        necessary; eg, the CLI.

        @exception SshError if the SSH connection has not yet been
                   established.

        @return An Paramiko channel that communicate with the remote end in
        a stateful way.
        """

        if (not self.is_connected()):
            raise SshError('Not connected!')

        channel = self.transport.open_session()
        channel.get_pty(term, 80, 24)
        channel.invoke_shell()
        channel.set_combine_stderr(True)
        return channel
