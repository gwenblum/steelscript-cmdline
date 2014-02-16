# Copyright 2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

from pq_runtime.exceptions import NbtError


class CmdlineException(NbtError):
    """Base exception representing an error executing the command line.

    :ivar command: The command that produced the error.
    :ivar output: The output returned.  None if the command did not return.
    """

    def __init__(self, command=None, output=None, _subclass_msg=None):
        """
        :param command: The command that produced the error.
        :param output: The output returned.  None if the command did not return.
        """
        self.command = command
        self.output = output
        if _subclass_msg is None:
            if output is None:
                if command is None:
                    msg = 'Unknown command line error'
                else:
                    msg = (("Command '%s' encountered an unknown error, "
                            "with no output.") % command)
            else:
                msg = ("Command '%s' encountered an error, with output '%s'" %
                       (command, output))
        else:
            msg = _subclass_msg
        super(CmdlineException, self).__init__(msg)


class CmdlineTimeout(CmdlineException):
    """Indicates a command was abandoned due to a timeout.

    Some timeouts within a given protocol may be reported as ConnectionError
    as the third-party libraries are not always specific about causes.
    However, all timeouts triggered in PQ code will raise this exception.

    :ivar command: The command we were trying to execute.
    :ivar timeout: The number of seconds that we were waiting for.
    """

    def __init__(self, command, timeout):
        """
        :param command: The command we were trying to execute.
        :param timeout: The number of seconds that we were waiting for.
        """
        self.timeout = timeout
        msg = ("Command '%s' timed out after %d seconds." % (command, timeout))
        super(CmdlineTimeout, self).__init__(command, _subclass_msg=msg)


class ConnectionError(CmdlineException):
    """Indicates a (probably) non-timeout error from the underlying protocol.

    May contain a wrapped exception from a third-party library.
    In Python 3 this would be on the __cause__ attribute.
    The third-party library may not use a specific exception for timeouts,
    so certain kinds of timeouts may appear as a ConnectionError.
    Timeouts managed by PQ code should use CmdlineTimeout instead.

    This exceptipn should be used to propagate errors up to levels
    that should not be aware of the specific underlying protocol.

    :ivar command: The command we were trying to execute.
    :ivar cause: The protocol-specific exception, if any, that triggered this.
    """

    def __init__(self, command=None, cause=None, context=None):
        """
        :param command: The command we were trying to execute.
        :param cause: The protocol-specific exception, if any,
                      that triggered this.
        :param context: An optional string describing the conetxt of the error.
        """

        self.cause = cause
        if command:
            msg = "Connection error while executing '%s'" % command
        else:
            msg = "Connection error."
        if context is not None:
            msg = "%s\n    Additional context: '%s'" % (msg, context)
        if cause is not None:
            msg = "%s\n    Underlying exception:\n%s" % (msg, cause)

        super(ConnectionError, self).__init__(command, _subclass_msg=msg)


class CmdlineError(CmdlineException):
    """Base for command responses that specifically indicate an error.

    See specific exceptions such as ``ShellError`` and ``CLIError`` for
    additional debugging fields.
    """
    pass


class ShellError(CmdlineError):
    """Exception representing a nonzero exit status from the shell.

    Technically, representing an unexpected exit from the shell, as some
    command, such as diff, have successful nonzero exits.

    :ivar command: The command that produced the error.
    :ivar exit_status: The exit status of the command.
    :ivar output: The output as returned by the shell, if any.
    """

    def __init__(self, command, exit_status, output=None):
        """
        :param command: The command that produced the error.
        :param exit_status: The exit status of the command.
        :param output: The output as returned by the shell, if any.
        """
        self.exit_status = exit_status
        msg = ("Command '%s exited with status %d, output: '%s'" %
               (command, exit_status,
                '<no output>' if output is None else output))
        super(ShellError, self).__init__(command, output=output,
                                         _subclass_msg=msg)


class CLIError(CmdlineError):
    """Exception representing an error message from the CLI.

    :ivar command: The command that produced the error.
    :ivar mode: The CLI mode we were in when the error occurred.
    :ivar output: The error string as returned by the CLI.
    """

    def __init__(self, command, mode, output=None):
        """
        :param command: The command that produced the error.
        :param mode: The CLI mode we were in when the error occurred.
        :param output: The error string as returned by the CLI.
        """
        self.mode = mode
        msg = ("Command '%s' in mode '%s' resulted in an error: '%s'" %
               (command, mode, '<no output>' if output is None else output))
        super(CLIError, self).__init__(command, output=output,
                                                _subclass_msg=msg)


class UnexpectedOutput(CmdlineException):
    """Exception for output where none should be, or output in the wrong format.

    This generally does not mean easily detectable error output, which is
    indicated by the appropriate subclass of ``CmdlineError``

    :ivar command: The command that produced the error.
    :ivar output: The output as returned from the command.
    :ivar expected_output: The output expected from the command, possibly None.
    """

    def __init__(self, command, output, expected_output=None):
        """
        :param command: The command that produced the error.
        :param output: The output as returned from the command.
        :param expected_output: The output expected from the command,
              possibly None.
        """
        self.expected_output = expected_output

        if expected_output is None:
            msg = (("Command '%s' returned output '%s' where none "
                    "was expected.") % (command, output))
        else:
            msg = (("Command '%s' returned the following output:\n"
                    "%s\ninstead of this expected output:\n%s") %
                   (command, output, expected_output))

        super(UnexpectedOutput, self).__init__(command, output=output,
                                               _subclass_msg=msg)


class UnknownCLIMode(CmdlineException):
    """Exception for any CLI (Riverbed or otherwise) sees an unknown mode."""

    def __init__(self, prompt):
        self.prompt = prompt
        super(UnknownCLIMode, self).__init__(
            _subclass_msg="Unknown CLI mode, prompt: '%s'" % prompt)
