# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.
from __future__ import (absolute_import, unicode_literals, print_function,
                        division)

from steelscript.cmdline.cli.ios_cli import IOS_CLI
from steelscript.cmdline.cli import CLIMode
from steelscript.cmdline import exceptions

import pytest
from mock import Mock, MagicMock

ANY_HOST = 'cisco-router1'
ANY_USER = 'user1'
ANY_PASSWORD = 'password1'
ANY_UNKNOWN_MODE = 'unknown'
ANY_SUB_INTERFACE = "gi1/1.555"
CONFIG_CMD = 'config terminal'

ANY_COMMAND = 'sh hosts'
ANY_COMMAND_OUTPUT = """Default domain is nbttech.com
Name/address lookup uses domain service
Name servers are 255.255.255.255

Codes: UN - unknown, EX - expired, OK - OK, ?? - revalidate
       temp - temporary, perm - permanent
              NA - Not Applicable None - Not defined

              Host                      Port  Flags      Age Type   Address(es)
              """
ANY_COMMAND_OUTPUT_DATA = '%s\n%s' % (ANY_COMMAND, ANY_COMMAND_OUTPUT)
ANY_COMMAND_ERROR = '% Unrecognized command'
ANY_COMMAND_ERROR_DATA = '%s\n%s' % (ANY_COMMAND, ANY_COMMAND_ERROR)


@pytest.fixture
def any_ios_cli():
    ios_cli = IOS_CLI(ANY_HOST, ANY_USER, ANY_PASSWORD)
    ios_cli.channel = Mock()
    return ios_cli


@pytest.fixture
def config_mode_match():
    fake_match = MagicMock()
    fake_match.re = MagicMock()
    fake_match.re.pattern = IOS_CLI.CLI_CONFIG_PROMPT
    return fake_match


@pytest.fixture
def cli_mock_output(any_ios_cli):
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_and_wait = MagicMock(name='method')
    return any_ios_cli


def test_current_cli_mode_at_normal_mode(any_ios_cli):
    mock_match = Mock()
    mock_match.re.pattern = any_ios_cli.CLI_NORMAL_PROMPT
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_line_and_wait.return_value = ('output', mock_match)
    current_mode = any_ios_cli.current_cli_mode()
    assert current_mode == CLIMode.NORMAL


def test_current_cli_mode_at_enable_mode(any_ios_cli):
    mock_match = Mock()
    mock_match.re.pattern = any_ios_cli.CLI_ENABLE_PROMPT
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_line_and_wait.return_value = ('output', mock_match)
    current_mode = any_ios_cli.current_cli_mode()
    assert current_mode == CLIMode.ENABLE


def test_current_cli_mode_at_config_mode(any_ios_cli):
    mock_match = Mock()
    mock_match.re.pattern = any_ios_cli.CLI_CONFIG_PROMPT
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_line_and_wait.return_value = ('output', mock_match)
    current_mode = any_ios_cli.current_cli_mode()
    assert current_mode == CLIMode.CONFIG


def test_current_cli_mode_at_subif_mode(any_ios_cli):
    mock_match = Mock()
    mock_match.re.pattern = any_ios_cli.CLI_SUBIF_PROMPT
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_line_and_wait.return_value = ('output', mock_match)
    current_mode = any_ios_cli.current_cli_mode()
    assert current_mode == CLIMode.SUBIF


def test_current_cli_mode_raise_at_unknown_mode(any_ios_cli):
    mock_match = Mock()
    mock_match.re.pattern = ANY_UNKNOWN_MODE
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_line_and_wait.return_value = ('output', mock_match)
    with pytest.raises(exceptions.UnknownCLIMode):
        any_ios_cli.current_cli_mode()


def test_enter_mode_normal_from_config_mode(any_ios_cli):
    any_ios_cli.current_cli_mode = MagicMock(name='method')
    any_ios_cli.current_cli_mode.return_value = CLIMode.CONFIG
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli.enter_mode_normal()
    any_ios_cli._send_line_and_wait.assert_any_call(
        'end', any_ios_cli.CLI_ENABLE_PROMPT)
    any_ios_cli._send_line_and_wait.assert_called_with(
        'disable', any_ios_cli.CLI_NORMAL_PROMPT)


def test_enter_mode_normal_from_enable_mode(any_ios_cli):
    any_ios_cli.current_cli_mode = MagicMock(name='method')
    any_ios_cli.current_cli_mode.return_value = CLIMode.ENABLE
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli.enter_mode_normal()
    any_ios_cli._send_line_and_wait.assert_called_with(
        'disable', any_ios_cli.CLI_NORMAL_PROMPT)


def test_enter_mode_normal_when_already_at_normal_mode(any_ios_cli):
    any_ios_cli.current_cli_mode = MagicMock(name='method')
    any_ios_cli.current_cli_mode.return_value = CLIMode.NORMAL
    any_ios_cli.enter_mode_normal()
    assert not any_ios_cli.channel._send_line_and_wait.called


def test_enter_mode_config_from_normal_mode(any_ios_cli):
    any_ios_cli.current_cli_mode = MagicMock(name='method')
    any_ios_cli.current_cli_mode.return_value = CLIMode.NORMAL
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._enable = MagicMock(name='method')
    any_ios_cli.enter_mode_config()
    assert any_ios_cli._enable.called
    any_ios_cli._send_line_and_wait.assert_called_with(
        'config terminal', any_ios_cli.CLI_CONFIG_PROMPT)


def test_enter_mode_config_from_enable_mode(any_ios_cli):
    any_ios_cli.current_cli_mode = MagicMock(name='method')
    any_ios_cli.current_cli_mode.return_value = CLIMode.ENABLE
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli.enter_mode_config()
    any_ios_cli._send_line_and_wait.assert_called_with(
        'config terminal', any_ios_cli.CLI_CONFIG_PROMPT)


def test_enter_mode_config_when_already_at_config_mode(any_ios_cli):
    any_ios_cli.current_cli_mode = MagicMock(name='method')
    any_ios_cli.current_cli_mode.return_value = CLIMode.CONFIG
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli.enter_mode_config()
    assert not any_ios_cli._send_line_and_wait.called


def test_enter_mode_subif_from_normal_mode(any_ios_cli):
    any_ios_cli.current_cli_mode = MagicMock(name='method')
    any_ios_cli.current_cli_mode.return_value = CLIMode.NORMAL
    any_ios_cli._enable = MagicMock(name='method')
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_line_and_wait.return_value = ('output', 'match')
    any_ios_cli.enter_mode_subif(ANY_SUB_INTERFACE)
    any_ios_cli._enable.assert_called_with()
    interface_cmd = 'interface ' + ANY_SUB_INTERFACE
    any_ios_cli._send_line_and_wait.assert_called_with(
        interface_cmd, any_ios_cli.CLI_SUBIF_PROMPT)
    any_ios_cli._send_line_and_wait.assert_any_call(
        CONFIG_CMD, any_ios_cli.CLI_CONFIG_PROMPT)


def test_enter_mode_subif_from_enable_mode(any_ios_cli):
    any_ios_cli.current_cli_mode = MagicMock(name='method')
    any_ios_cli.current_cli_mode.return_value = CLIMode.ENABLE
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_line_and_wait.return_value = ('output', 'match')
    any_ios_cli.enter_mode_subif(ANY_SUB_INTERFACE)
    interface_cmd = 'interface ' + ANY_SUB_INTERFACE
    any_ios_cli._send_line_and_wait.assert_called_with(
        interface_cmd, any_ios_cli.CLI_SUBIF_PROMPT)
    any_ios_cli._send_line_and_wait.assert_any_call(
        CONFIG_CMD, any_ios_cli.CLI_CONFIG_PROMPT)


def test_enter_mode_subif_from_config_mode(any_ios_cli):
    any_ios_cli.current_cli_mode = MagicMock(name='method')
    any_ios_cli.current_cli_mode.return_value = CLIMode.CONFIG
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_line_and_wait.return_value = ('output', 'match')
    any_ios_cli.enter_mode_subif(ANY_SUB_INTERFACE)
    interface_cmd = 'interface ' + ANY_SUB_INTERFACE
    any_ios_cli._send_line_and_wait.assert_called_with(
        interface_cmd, any_ios_cli.CLI_SUBIF_PROMPT)


def test_enter_mode_subif_from_subif_mode(any_ios_cli):
    any_ios_cli.current_cli_mode = MagicMock(name='method')
    any_ios_cli.current_cli_mode.return_value = CLIMode.SUBIF
    any_ios_cli._send_line_and_wait = MagicMock(name='method')
    any_ios_cli._send_line_and_wait.return_value = ('output', 'match')
    any_ios_cli.enter_mode_subif(ANY_SUB_INTERFACE)
    interface_cmd = 'interface ' + ANY_SUB_INTERFACE
    any_ios_cli._send_line_and_wait.assert_called_with(
        interface_cmd, any_ios_cli.CLI_SUBIF_PROMPT)


def test_exec_command_output(cli_mock_output, config_mode_match):
    cmo = cli_mock_output
    cmo._send_line_and_wait.return_value = (ANY_COMMAND_OUTPUT_DATA,
                                            config_mode_match)

    assert cmo.exec_command(ANY_COMMAND) == ANY_COMMAND_OUTPUT
    assert cmo.exec_command(ANY_COMMAND,
                            output_expected=True) == ANY_COMMAND_OUTPUT
    with pytest.raises(exceptions.UnexpectedOutput):
        cmo.exec_command(ANY_COMMAND, output_expected=False)


def test_exec_command_no_output(cli_mock_output, config_mode_match):
    cmo = cli_mock_output
    cmo._send_line_and_wait.return_value = ('%s\n' % ANY_COMMAND,
                                            config_mode_match)
    assert cmo.exec_command(ANY_COMMAND) == ''
    assert cmo.exec_command(ANY_COMMAND, output_expected=False) == ''
    with pytest.raises(exceptions.UnexpectedOutput):
        cmo.exec_command(ANY_COMMAND, output_expected=True)


def test_exec_command_error(cli_mock_output, config_mode_match):
    cmo = cli_mock_output
    cmo._send_line_and_wait.return_value = (ANY_COMMAND_ERROR_DATA,
                                            config_mode_match)
    assert cmo.exec_command(ANY_COMMAND,
                            error_expected=True) == ANY_COMMAND_ERROR
    assert cmo.exec_command(ANY_COMMAND,
                            output_expected=False,
                            error_expected=True) == ANY_COMMAND_ERROR
    assert cmo.exec_command(ANY_COMMAND,
                            output_expected=True,
                            error_expected=True) == ANY_COMMAND_ERROR
    with pytest.raises(exceptions.CLIError):
        cmo.exec_command(ANY_COMMAND, output_expected=True)
    with pytest.raises(exceptions.CLIError):
        cmo.exec_command(ANY_COMMAND, output_expected=False)
    with pytest.raises(exceptions.CLIError):
        cmo.exec_command(ANY_COMMAND, output_expected=None)
