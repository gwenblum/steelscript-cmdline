# Copyright 2014 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

import pytest
from mock import Mock, MagicMock

from pq_cmdline import exceptions
from pq_cmdline.powershell import PowerShell

ANY_COMMAND = 'show date'
ANY_COMMAND_OUTPUT = 'Thu Sep 12 19:50:51 GMT 2013'
ANY_COMMAND_OUTPUT_DATA = '%s\n%s' % (ANY_COMMAND, ANY_COMMAND_OUTPUT)
ANY_ROOT_COMMAND = 'show'
ANY_TIMEOUT = 120


@pytest.fixture
def any_powershell():
    channel = Mock()
    powershell = PowerShell(channel)
    return powershell


@pytest.fixture
def powershell_mock_output(any_powershell):
    any_powershell._send_line_and_wait = MagicMock(name='method')
    return any_powershell


@pytest.fixture
def prompt_match():
    fake_match = MagicMock()
    fake_match.re = MagicMock()
    fake_match.re.pattern = PowerShell.POWERSHELL_PROMPT
    return fake_match


def test_start_with_default_prompt(any_powershell):
    any_powershell.start()
    default_prompt = PowerShell.POWERSHELL_PROMPT
    any_powershell.channel.start.assert_called_with(default_prompt)


def test_start_with_non_default_prompt(any_powershell):
    any_prompt = 'any prompt'
    any_powershell.start(any_prompt)
    any_powershell.channel.start.assert_called_with(any_prompt)


def test_exec_command_output(powershell_mock_output, prompt_match):
    cmo = powershell_mock_output
    cmo._send_line_and_wait.return_value = (ANY_COMMAND_OUTPUT_DATA,
                                            prompt_match)

    assert cmo.exec_command(ANY_COMMAND) == ANY_COMMAND_OUTPUT
    assert cmo.exec_command(ANY_COMMAND,
                            output_expected=True) == ANY_COMMAND_OUTPUT
    with pytest.raises(exceptions.UnexpectedOutput):
        cmo.exec_command(ANY_COMMAND, output_expected=False)


def test_exec_command_no_output(powershell_mock_output, prompt_match):
    cmo = powershell_mock_output
    cmo._send_line_and_wait.return_value = ('%s\n' % ANY_COMMAND,
                                            prompt_match)
    assert cmo.exec_command(ANY_COMMAND) == ''
    assert cmo.exec_command(ANY_COMMAND, output_expected=False) == ''
    with pytest.raises(exceptions.UnexpectedOutput):
        cmo.exec_command(ANY_COMMAND, output_expected=True)
