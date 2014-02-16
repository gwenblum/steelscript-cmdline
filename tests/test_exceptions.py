# Copyright 2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

from pq_cmdline.exceptions import (
    CmdlineException, CmdlineTimeout, UnexpectedOutput, UnknownCLIMode,
    CmdlineError, ShellError, CLIError, ConnectionError
)

ANY_COMMAND = 'do some stuff'
ANY_OUTPUT = 'here is your stuff'
ANY_EXPECTED_OUTPUT = 'not the same as output'
ANY_NONZERO_STATUS = -1
ANY_MODE = 'config'
ANY_TIMEOUT = 60
ANY_CONTEXT = "blah explanation whatever"
ANY_UNKNOWN_CLI_PROMPT = "C:\ "


def test_cmdline_exception_no_args():
    e = CmdlineException()
    assert e.command is None
    assert e.output is None
    assert unicode(e) == 'Unknown command line error'


def test_cmdline_exception():
    e = CmdlineException(ANY_COMMAND, output=ANY_OUTPUT)
    assert e.command is ANY_COMMAND
    assert e.output is ANY_OUTPUT

    msg = unicode(e)
    assert e.command in msg
    assert e.output in msg


def test_timeout():
    e = CmdlineTimeout(ANY_COMMAND, timeout=ANY_TIMEOUT)
    assert e.command is ANY_COMMAND
    assert e.output is None
    assert e.timeout == ANY_TIMEOUT

    msg = unicode(e)
    assert e.command in msg
    assert unicode(e.timeout) in msg


def test_connection_error():
    e = ConnectionError(ANY_COMMAND, context=ANY_CONTEXT)
    assert e.command is ANY_COMMAND

    msg = unicode(e)
    assert e.command in msg
    assert ANY_CONTEXT in msg


def test_connection_no_command_with_cause():
    try:
        raise Exception("whatever")
    except Exception as ex:
        e = ConnectionError(cause=ex)
        assert e.command is None
        assert e.cause is ex

        msg = unicode(e)
        ex_msg = unicode(ex)
        assert ex_msg in msg


def test_shell_error():
    e = ShellError(ANY_COMMAND, output=ANY_OUTPUT,
                   exit_status=ANY_NONZERO_STATUS)
    assert e.command is ANY_COMMAND
    assert e.output is ANY_OUTPUT
    assert e.exit_status is ANY_NONZERO_STATUS

    msg = unicode(e)
    assert e.command in msg
    assert e.output in msg
    assert unicode(e.exit_status) in msg


def test_shell_error_no_output():
    e = ShellError(ANY_COMMAND, exit_status=ANY_NONZERO_STATUS)
    assert e.command is ANY_COMMAND
    assert e.output is None
    assert e.exit_status is ANY_NONZERO_STATUS

    msg = unicode(e)
    assert e.command in msg
    assert unicode(e.exit_status) in msg


def test_cli_error():
    e = CLIError(ANY_COMMAND, output=ANY_OUTPUT, mode=ANY_MODE)
    assert e.command is ANY_COMMAND
    assert e.output is ANY_OUTPUT
    assert e.mode is ANY_MODE

    msg = unicode(e)
    assert e.command in msg
    assert e.output in msg
    assert e.mode in msg


def test_cli_error_no_output():
    e = CLIError(ANY_COMMAND, mode=ANY_MODE)
    assert e.command is ANY_COMMAND
    assert e.output is None
    assert e.mode is ANY_MODE

    msg = unicode(e)
    assert e.command in msg
    assert e.mode in msg


def test_unkexpected_output_vs_none():
    e = UnexpectedOutput(ANY_COMMAND, output=ANY_OUTPUT)
    assert e.command is ANY_COMMAND
    assert e.output is ANY_OUTPUT
    assert e.expected_output is None

    msg = unicode(e)
    assert e.command in msg
    assert e.output in msg
    assert 'none was expected' in msg

def test_unkexpected_output():
    e = UnexpectedOutput(ANY_COMMAND, output=ANY_OUTPUT,
                         expected_output=ANY_EXPECTED_OUTPUT)
    assert e.command is ANY_COMMAND
    assert e.output is ANY_OUTPUT
    assert e.expected_output is ANY_EXPECTED_OUTPUT

    msg = unicode(e)
    assert e.command in msg
    assert e.output in msg
    assert e.expected_output in msg


def test_unknown_cli_mode():
    e = UnknownCLIMode(prompt=ANY_UNKNOWN_CLI_PROMPT)
    print(e.command)
    print(e.output)
    print(e.prompt)
    assert e.command is None
    assert e.output is None
    assert e.prompt is ANY_UNKNOWN_CLI_PROMPT

    msg = unicode(e)
    assert e.prompt in msg
