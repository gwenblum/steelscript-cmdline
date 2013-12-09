# $Id $ 
#
# Copyright 2009-2013 Riverbed Technology, Inc.
# All Rights Reserved. Confidential.

import pytest
import logging

from pq_cmdline.sshshell import SshShell
from pq_cmdline.cli import Cli
from pq_cmdline.interactive_channel import InteractiveChannel

logging.basicConfig(level=logging.DEBUG)

@pytest.mark.skipif("not config.getvalue('host')")
def test_shell():
    logger = logging.getLogger('test_shell')
    host = pytest.config.getoption('--host')
    user = pytest.config.getoption('--user')
    password = pytest.config.getoption('--password')
    sh = SshShell(host, user, password)
    sh.connect()
    (output, exitstatus) = sh.exec_command("pwd")
    logger.debug("pwd output %s" % output)
    assert exitstatus == 0
    sh.disconnect()

@pytest.mark.skipif("not config.getvalue('host')")
def test_exec_command():
    """
    Test exec_command() without doing connect() explicitly first. In this case
    it will do connect() inside exec_command().
    """
    logger = logging.getLogger('test_exec_command')
    host = pytest.config.getoption('--host')
    user = pytest.config.getoption('--user')
    password = pytest.config.getoption('--password')
    sh = SshShell(host, user, password)
    (output, exitstatus) = sh.exec_command("pwd")
    logger.debug("pwd output %s" % output)
    assert exitstatus == 0
    sh.disconnect()

@pytest.mark.skipif("not config.getvalue('host')")
def test_cli():
    logger = logging.getLogger('test_cli')
    
    host = pytest.config.getoption('--host')
    user = pytest.config.getoption('--user')
    password = pytest.config.getoption('--password')
    
    sh = SshShell(host, user, password)
    sh.connect()
    cli = Cli(InteractiveChannel(sh, host))
    cli.start()
    cli.enter_level_config()
    output = cli.run_command("show version concise")
    logger.debug("version: %s" % output)
    cli.stop()
    sh.disconnect()
    
