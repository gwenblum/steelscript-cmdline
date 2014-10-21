SteelScript Command Line Sources
================================

.. automodule:: steelscript.cmdline.cli

.. currentmodule:: steelscript.cmdline.cli.__init__

:py:class:`CLI` Objects
-------------------------------

.. autoclass:: CLI
   :members:

.. currentmodule:: steelscript.cmdline.cli.ios_cli

:py:class:`IOS_CLI` Objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: IOS_CLI
   :members:
   :inherited-members:
   :show-inheritance:

.. currentmodule:: steelscript.cmdline.cli.rvbd_cli

:py:class:`RVBD_CLI` Objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: RVBD_CLI
   :members:
   :inherited-members:
   :show-inheritance:

.. currentmodule:: steelscript.cmdline.cli.vyatta_cli

:py:class:`VyattaCLI` Objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: VyattaCLI
   :members:
   :inherited-members:
   :show-inheritance:

.. automodule:: steelscript.cmdline.channel

.. currentmodule:: steelscript.cmdline.channel

:py:class:`Channel` Objects
---------------------------

.. autoclass:: Channel
   :members:
   
.. automodule:: steelscript.cmdline.exceptions

.. currentmodule:: steelscript.cmdline.exceptions

:py:class:`CmdlineException` Objects
------------------------------------

.. autoclass:: CmdlineException
   :members:

:py:class:`CmdlineTimeout` Objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: CmdlineTimeout
   :members:
   :inherited-members:
   :show-inheritance:

:py:class:`ConnectionError` Objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: ConnectionError
   :members:
   :inherited-members:
   :show-inheritance:


:py:class:`CLINotRunning` Objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: CLINotRunning
   :members:
   :inherited-members:
   :show-inheritance:

:py:class:`CmdlineError` Objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: CmdlineError
   :members:
   :inherited-members:
   :show-inheritance:

:py:class:`ShellError` Objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: ShellError
   :members:
   :inherited-members:
   :show-inheritance:

:py:class:`CLIError` Objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: CLIError
   :members:
   :inherited-members:
   :show-inheritance:

:py:class:`UnexpectedOutput` Objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: UnexpectedOutput
   :members:
   :inherited-members:
   :show-inheritance:

:py:class:`UnknownCLIMode` Objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: UnknownCLIMode
   :members:
   :inherited-members:
   :show-inheritance:

.. automodule:: steelscript.cmdline.libvirtchannel

.. currentmodule:: steelscript.cmdline.libvirtchannel

:py:class:`LibVirtChannel` Objects
------------------------------------

.. autoclass:: LibVirtChannel
   :members:

.. automodule:: steelscript.cmdline.powershell

.. currentmodule:: steelscript.cmdline.powershell

:py:class:`PowerShell` Objects
------------------------------------

.. autoclass:: PowerShell
   :members:

.. automodule:: steelscript.cmdline.shell

.. currentmodule:: steelscript.cmdline.shell

:py:class:`Shell` Objects
------------------------------------

.. autoclass:: Shell
   :members:

.. automodule:: steelscript.cmdline.sshchannel

.. currentmodule:: steelscript.cmdline.sshchannel

:py:class:`SSHChannel` Objects
------------------------------------

.. autoclass:: SSHChannel
   :members:

.. automodule:: steelscript.cmdline.sshprocess

.. currentmodule:: steelscript.cmdline.sshprocess

:py:class:`SSHProcess` Objects
------------------------------------

.. autoclass:: SSHProcess
   :members:

.. automodule:: steelscript.cmdline.telnetchannel

.. currentmodule:: steelscript.cmdline.telnetchannel

:py:class:`TelnetChannel` Objects
------------------------------------

.. autoclass:: TelnetChannel
   :members:

.. automodule:: steelscript.cmdline.transport

.. currentmodule:: steelscript.cmdline.transport

:py:class:`Transport` Objects
------------------------------------

.. autoclass:: Transport
   :members:


Parsers
---------

.. automodule:: steelscript.cmdline.parsers

Functions for parsing command line responses

.. autofunction:: cli_parse_basic
.. autofunction:: cli_parse_table
.. autofunction:: check_numeric
.. autofunction:: enable_squash
.. autofunction:: parse_boolean
.. autofunction:: restart_required
.. autofunction:: reboot_required
.. autofunction:: parse_ip_and_port
.. autofunction:: parse_url_to_host_port_protocol
.. autofunction:: parse_saasinfo_data



