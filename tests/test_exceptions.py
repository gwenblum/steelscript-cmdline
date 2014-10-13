# Copyright 2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)
import re

import pytest

from steelscript.cmdline.exceptions import (
    CmdlineException, CmdlineTimeout, UnexpectedOutput, UnknownCLIMode,
    ShellError, CLIError, ConnectionError, CLINotRunning,
)

ANY_COMMAND = 'do some stuff'
ANY_OUTPUT = 'here is your stuff'
ANY_EXPECTED_OUTPUT = 'not the same as output'
ANY_NONZERO_STATUS = -1
ANY_MODE = 'config'
ANY_TIMEOUT = 60
ANY_CONTEXT = "blah explanation whatever"
ANY_UNKNOWN_CLI_PROMPT = "C:\ "
ANY_CLI_CRASH_TEXT = 'whoops'
ANY_SIMPLE_MATCH = 'match this'
ANY_MATCH_FROM_PATTERN = '^a compiled pattern$'
ANY_MATCH_FROM_RESULT = 'match result [a-z]+'


@pytest.fixture
def any_complex_match():
    return [
        re.compile(ANY_MATCH_FROM_PATTERN),
        re.search(ANY_MATCH_FROM_RESULT, 'string for match result abcdefg'),
    ]


def test_cmdline_exception_no_args():
    e = CmdlineException()
    assert e.command is None
    assert e.output is None
    assert unicode(e) == 'Unknown command line error'


def test_cmdline_exception():
    e = CmdlineException(command=ANY_COMMAND, output=ANY_OUTPUT)
    assert e.command is ANY_COMMAND
    assert e.output is ANY_OUTPUT

    msg = unicode(e)
    assert e.command in msg
    assert e.output in msg


def test_timeout():
    e = CmdlineTimeout(command=ANY_COMMAND, timeout=ANY_TIMEOUT)
    assert e.command is ANY_COMMAND
    assert e.output is None
    assert e.timeout == ANY_TIMEOUT
    assert e.failed_match_pattern is None

    msg = unicode(e)
    assert e.command in msg
    assert unicode(e.timeout) in msg


def test_timeout_output_complex_failed_match(any_complex_match):
    e = CmdlineTimeout(command=ANY_COMMAND, output=ANY_OUTPUT,
                       timeout=ANY_TIMEOUT, failed_match=any_complex_match)
    assert e.command is ANY_COMMAND
    assert e.output is None
    assert e.timeout == ANY_TIMEOUT
    for m in (ANY_MATCH_FROM_PATTERN, ANY_MATCH_FROM_RESULT):
        assert m in e.failed_match_pattern

    msg = unicode(e)
    assert e.command in msg
    assert unicode(e.timeout) in msg
    assert e.failed_match_pattern in msg


def test_connection_error():
    e = ConnectionError(command=ANY_COMMAND, context=ANY_CONTEXT)
    assert e.command is ANY_COMMAND
    assert e.cause is None

    msg = unicode(e)
    assert e.command in msg
    assert ANY_CONTEXT in msg


def test_connection_error_with_simple_failed_match():
    e = ConnectionError(command=ANY_COMMAND, failed_match=ANY_SIMPLE_MATCH)
    assert e.command is ANY_COMMAND
    assert e.cause is None
    assert ANY_SIMPLE_MATCH in e.failed_match_pattern

    msg = unicode(e)
    assert e.command in msg
    assert ANY_SIMPLE_MATCH in msg


def test_connection_no_command_with_cause():
    try:
        raise Exception("whatever")
    except Exception as ex:
        e = ConnectionError(cause=ex)
        assert e.command is None
        assert e.cause is ex
        assert e.failed_match_pattern is None

        msg = unicode(e)
        ex_msg = unicode(ex)
        assert ex_msg in msg


def test_cli_could_not_start():
    e = CLINotRunning(output=ANY_CLI_CRASH_TEXT)
    msg = unicode(e)
    assert 'not start' in msg
    assert ANY_CLI_CRASH_TEXT in msg


def test_cli_not_running():
    e = CLINotRunning()
    assert 'not running' in unicode(e)


def test_shell_error():
    e = ShellError(command=ANY_COMMAND, output=ANY_OUTPUT,
                   exit_status=ANY_NONZERO_STATUS)
    assert e.command is ANY_COMMAND
    assert e.output is ANY_OUTPUT
    assert e.exit_status is ANY_NONZERO_STATUS

    msg = unicode(e)
    assert e.command in msg
    assert e.output in msg
    assert unicode(e.exit_status) in msg


def test_shell_error_no_output():
    e = ShellError(command=ANY_COMMAND, exit_status=ANY_NONZERO_STATUS)
    assert e.command is ANY_COMMAND
    assert e.output is None
    assert e.exit_status is ANY_NONZERO_STATUS

    msg = unicode(e)
    assert e.command in msg
    assert unicode(e.exit_status) in msg


def test_cli_error():
    e = CLIError(command=ANY_COMMAND, output=ANY_OUTPUT, mode=ANY_MODE)
    assert e.command is ANY_COMMAND
    assert e.output is ANY_OUTPUT
    assert e.mode is ANY_MODE

    msg = unicode(e)
    assert e.command in msg
    assert e.output in msg
    assert e.mode in msg


def test_cli_error_no_output():
    e = CLIError(command=ANY_COMMAND, mode=ANY_MODE)
    assert e.command is ANY_COMMAND
    assert e.output is None
    assert e.mode is ANY_MODE

    msg = unicode(e)
    assert e.command in msg
    assert e.mode in msg


def test_unexpected_output_vs_none():
    e = UnexpectedOutput(command=ANY_COMMAND, output=ANY_OUTPUT)
    assert e.command is ANY_COMMAND
    assert e.output is ANY_OUTPUT
    assert e.expected_output is None

    msg = unicode(e)
    assert e.command in msg
    assert e.output in msg
    assert 'none was expected' in msg


def test_unexpected_output_none_vs_expected():
    e = UnexpectedOutput(command=ANY_COMMAND, output=None,
                         expected_output=ANY_EXPECTED_OUTPUT)
    assert e.command is ANY_COMMAND
    assert e.output is None
    assert e.expected_output is ANY_EXPECTED_OUTPUT

    msg = unicode(e)
    assert e.command in msg
    assert 'no output' in msg
    assert e.expected_output in msg


def test_unexpected_output_none_vs_unspecified():
    e = UnexpectedOutput(command=ANY_COMMAND, output=None,
                         expected_output=True)
    assert e.command is ANY_COMMAND
    assert e.output is None
    assert e.expected_output is True

    msg = unicode(e)
    assert e.command in msg
    assert 'no output' in msg
    assert 'unspecified output' in msg


def test_unexpected_output():
    e = UnexpectedOutput(command=ANY_COMMAND, output=ANY_OUTPUT,
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
    assert e.command is None
    assert e.output is None
    assert e.prompt is ANY_UNKNOWN_CLI_PROMPT

    msg = unicode(e)
    assert e.prompt in msg
