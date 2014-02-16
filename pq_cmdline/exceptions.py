# Copyright 2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

from pq_runtime.exceptions import NbtError


class CmdlineException(NbtError):
    """Base exception representing an error executing the command line.

    :param command: The command that produced the error.
    :param output: The output returned.  None if the command did not return.

    :ivar command: The command that produced the error.
    :ivar output: The output returned.  None if the command did not return.
    """
    def __init__(self, command, output=None, _subclass_msg=None):
        self.command = command
        self.output = output
        if _subclass_msg is None:
            if output is None:
                msg = (("Command '%s' encountered an unknown error, "
                        "with no output.") % command)
            else:
                msg = ("Command '%s' encountered an error, with output '%s'" %
                       (command, output))
        else:
            msg = _subclass_msg
        super(CmdlineException, self).__init__(msg)


class CmdlineTimeout(CmdlineException):
    def __init__(self, command, timeout):
        self.timeout = timeout
        msg = ("Command '%s' timed out after %d seconds." % (command, timeout))
        super(CmdlineTimeout, self).__init__(command, _subclass_msg=msg)


class ConnectionError(CmdlineException):
    """Indicates a non-timeout error from the underlying protocol.

    May contain a wrapped exception from a third-party library.
    In Python 3 this would be on the __cause__ attribute.

    This exceptipn should be used to propagate errors up to levels
    that should not be aware of the specific underlying protocol.

    :param cause: The protocol-specific exception, if any, that triggered this.
    :param context: An optional string describing the conetxt of the error.

    :ivar cause: The protocol-specific exception, if any, that triggered this.
    """

    def __init__(self, command=None, cause=None, context=None):
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

    :param command: The command that produced the error.
    :param exit_status: The exit status of the command.
    :param output: The output as returned by the shell, if any.

    :ivar command: The command that produced the error.
    :ivar exit_status: The exit status of the command.
    :ivar output: The output as returned by the shell, if any.
    """
    def __init__(self, command, exit_status, output=None):
        self.exit_status = exit_status
        msg = ("Command '%s exited with status %d, output: '%s'" %
               (command, exit_status,
                '<no output>' if output is None else output))
        super(ShellError, self).__init__(command, output=output,
                                         _subclass_msg=msg)


class CLIError(CmdlineError):
    """Exception representing an error message from the CLI.

    :param command: The command that produced the error.
    :param mode: The CLI mode we were in when the error occurred.
    :param output: The error string as returned by the CLI.

    :ivar command: The command that produced the error.
    :ivar mode: The CLI mode we were in when the error occurred.
    :ivar output: The error string as returned by the CLI.
    """

    def __init__(self, command, mode, output=None):
        self.mode = mode
        msg = ("Command '%s' in mode '%s' resulted in an error: '%s'" %
               (command, mode, '<no output>' if output is None else output))
        super(CLIError, self).__init__(command, output=output,
                                                _subclass_msg=msg)


class UnexpectedOutput(CmdlineException):
    """Exception for output where none should be, or output in the wrong format.

    This generally does not mean easily detectable error output, which is
    indicated by the appropriate subclass of ``CmdlineError``
    """

    def __init__(self, command, output, expected_output=None):
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
