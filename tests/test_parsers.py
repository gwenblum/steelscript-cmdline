# $Id $
#
# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import pytest

from steelscript.cmdline import parsers
from steelscript.cmdline.exceptions import UnexpectedOutput

import ipaddress
import logging

ANY_CLI_OUTPUT = """key:         value
foo:            bar
stuff:          junk
numbers:    1 / 2 / 3
measurements:   15 Flg / 10 Wuzzits
time:   12d 15h 3m 10s
date: 2013-11-11 11:15:29"""

IP_ROUTE_TABLE = """
Destination       Mask              Gateway           Interface
10.3.0.0          255.255.248.0     0.0.0.0           aux
invalid                             DNE               aux
default           0.0.0.0           10.3.0.1
"""
IP_ROUTE_HEADERS = ['destination', 'mask', 'gateway', 'interface']
EXPECTED_IP_ROUTE_TABLE =\
    [{'destination': '10.3.0.0',
      'mask': '255.255.248.0',
      'gateway': '0.0.0.0',
      'interface': 'aux'},
     {'destination': 'invalid',
      'gateway': 'DNE',
      'interface': 'aux'},
     {'destination': 'default',
      'mask': '0.0.0.0',
      'gateway': '10.3.0.1'}]

IOSTAT_TABLE = """
Device:            tps   Blk_read/s   Blk_wrtn/s   Blk_read   Blk_wrtn
sdb              50.49      3512.63       901.42 23683610051 6077756099
md0             454.11      1316.46      2682.91 8876085606 18089282052
dm-1              0.00         0.00         0.00       2330          0
"""
IOSTAT_HEADERS =\
    ['Device:', 'tps', 'Blk_read/s', 'Blk_wrtn/s', 'Blk_read', 'Blk_wrtn']
EXPECTED_IOSTAT_TABLE =\
    [{'device:': 'sdb',
      'tps': '50.49',
      'blk_read/s': '3512.63',
      'blk_wrtn/s': '901.42',
      'blk_read': '23683610051',
      'blk_wrtn': '6077756099'},
     {'device:': 'md0',
      'tps': '454.11',
      'blk_read/s': '1316.46',
      'blk_wrtn/s': '2682.91',
      'blk_read': '8876085606',
      'blk_wrtn': '18089282052'},
     {'device:': 'dm-1',
      'tps': '0.00',
      'blk_read/s': '0.00',
      'blk_wrtn/s': '0.00',
      'blk_read': '2330',
      'blk_wrtn': '0'}]

SPACES_TABLE = """
  Spaced          column 2
  ------          --------
  data1           data 2
  data 1

                  after blank line
"""
SPACES_TABLE_HEADERS = ['Spaced', 'column 2']
EXPECTED_SPACES_TABLE =\
    [{'spaced': 'data1',
      'column 2': 'data 2'},
     {'spaced': 'data 1'},
     {'column 2': 'after blank line'}]

BOUNDS_TABLE = """
Column1           Column2          Column3
            right-aligned
                  left-aligned
                    in
             over both sides
                  perfect
"""
BOUNDS_TABLE_HEADERS = ['Column1', 'Column2', 'Column3']
EXPECTED_BOUNDS_TABLE =\
    [{'column2': 'right-aligned'},
     {'column2': 'left-aligned'},
     {'column2': 'in'},
     {'column2': 'over both sides'},
     {'column2': 'perfect'}]

INVALID_TABLE = """
Column1         Column2
   under two headers
"""
INVALID_TABLE_HEADERS = ['Column1', 'Column2']

INVALID_TABLE2 = """
Column1                  Column2
       not under anything
"""
INVALID_TABLE2_HEADERS = ['Column1', 'Column2']

ANY_REPEAT_OUTPUT = """key:         value
key:            value"""

ANY_EMPTY_OUTPUT = "key:             "

ANY_NUMERICS_OUTPUT = """key:        string_value
key2:       numeric 10 with string
key3:       10
key4:       10.5
key5:       10.5.10.1"""

ANY_MULTIPLE_ENABLED = """enabled: True
another enabled: False"""

ANY_WOULD_BE_BOOLEAN = 'yes'
ANY_FAKE_BOOLEAN = 'yesman'
ANY_BOOLEAN_STRING = 'False'

RESTART_NEEDED_STRING1 = "You must restart the service for your changes \
to take effect."
RESTART_NEEDED_STRING2 = "<<Service needs a 'restart' for this \
config to take effect>>"
RESTART_NEEDED_STRING3 = "You must restart the optimization service for \
your changes to take effect."
REBOOT_NEEDED_STRING1 = "Please save your configuration and reboot the \
appliance for your changes to take effect."

IP_PORT_INPUT = "1.1.1.1:2000"
EXPECTED_IP_PORT_INPUT =\
    {'ip': ipaddress.ip_address(u'1.1.1.1'), 'port': '2000'}

PARSE_URL_TO_HOST_PORT_PROTOCOL_INPUT = "http://blah.com"
EXPECTED_PARSE_URL_TO_HOST_PORT_PROTOCOL_OUTPUT =\
    {'host': 'blah.com', 'port': 80, 'protocol': 'http'}

PARSE_SAASINFO_DATA_GARBAGE_INPUT = "Garbage"

PARSE_SAASINFO_DATA_INPUT = '''\
=================================
SaaS Application
=================================
O365

=================================
SaaS IP
=================================
10.41.222.0/24 [0-65535]
111.221.112.0/21 [1-65535]
111.221.116.0/24 [1-65535]
111.221.17.160/27 [1-65535]
111.221.20.128/25 [0-65535]

=================================
SaaS Hostname
=================================
*.mail.apac.example.com
*.example1.com
*.example2.com
example1.com

=================================
GeoDNS
=================================
---------------------------------
MBX Region
---------------------------------
blu nam.ca.bay-area
apc nam.ca.bay-area
xyz nam.ca.bay-area
abc nam.tx.san-antonio
---------------------------------
Regional IPs
---------------------------------
nam.ca.bay-area
132.245.80.146
132.245.80.150
nam.tx.san-antonio
132.245.80.153
132.245.80.156
132.245.81.114
'''

EXPECTED_PARSE_SAASINFO_DATA_OUTPUT =\
    {'appid': 'O365',
     'ip': ['10.41.222.0/24 [0-65535]',
            '111.221.112.0/21 [1-65535]',
            '111.221.116.0/24 [1-65535]',
            '111.221.17.160/27 [1-65535]',
            '111.221.20.128/25 [0-65535]'],
     'host': ['*.mail.apac.example.com',
              '*.example1.com',
              '*.example2.com',
              'example1.com'],
     'geodns': {'nam.ca.bay-area': {'mbx': ['blu',
                                            'apc',
                                            'xyz'],
                                    'ip': ['132.245.80.146',
                                           '132.245.80.150']},
                'nam.tx.san-antonio': {'mbx': ['abc'],
                                       'ip': ['132.245.80.153',
                                              '132.245.80.156',
                                              '132.245.81.114']}}}


logging.basicConfig(level=logging.INFO)


def test_cli_parse_basic():
    parsed_output = parsers.cli_parse_basic(ANY_CLI_OUTPUT)
    assert parsed_output['key'] == 'value'
    assert parsed_output['foo'] == 'bar'
    assert parsed_output['numbers'] == '1 / 2 / 3'
    assert parsed_output['measurements'] == '15 Flg / 10 Wuzzits'
    assert parsed_output['time'] == '12d 15h 3m 10s'
    assert parsed_output['date'] == '2013-11-11 11:15:29'


def test_cli_parse_table_ip_routes():
    parsed_output = parsers.cli_parse_table(IP_ROUTE_TABLE, IP_ROUTE_HEADERS)
    assert parsed_output == EXPECTED_IP_ROUTE_TABLE


def test_cli_parse_table_iostat():
    parsed_output = parsers.cli_parse_table(IOSTAT_TABLE, IOSTAT_HEADERS)
    assert parsed_output == EXPECTED_IOSTAT_TABLE


def test_cli_parse_table_with_spaces():
    parsed_output = parsers.cli_parse_table(SPACES_TABLE, SPACES_TABLE_HEADERS)
    assert parsed_output == EXPECTED_SPACES_TABLE


def test_cli_parse_table_bounds():
    parsed_output = parsers.cli_parse_table(BOUNDS_TABLE, BOUNDS_TABLE_HEADERS)
    assert parsed_output == EXPECTED_BOUNDS_TABLE


def test_cli_parse_table_long_item_fails():
    with pytest.raises(UnexpectedOutput) as e:
        parsers.cli_parse_table(INVALID_TABLE, INVALID_TABLE_HEADERS)
    assert "under two headers" in e.value.message


def test_cli_parse_table_not_under_header_fails():
    with pytest.raises(UnexpectedOutput) as e:
        parsers.cli_parse_table(INVALID_TABLE2, INVALID_TABLE2_HEADERS)
    assert "not under anything" in e.value.message


def test_parse_boolean():
    with pytest.raises(ValueError):
        assert parsers.parse_boolean(ANY_FAKE_BOOLEAN)
    assert parsers.parse_boolean(ANY_WOULD_BE_BOOLEAN) is True
    assert parsers.parse_boolean(ANY_BOOLEAN_STRING) is False


def test_restart_required_with_string1():
    input = ANY_CLI_OUTPUT + "\n" + RESTART_NEEDED_STRING1
    result = parsers.restart_required(input)

    assert (result)


def test_restart_required_with_string2():
    input = ANY_CLI_OUTPUT + "\n" + RESTART_NEEDED_STRING2
    result = parsers.restart_required(input)

    assert (result)


def test_restart_required_with_string3():
    input = ANY_CLI_OUTPUT + "\n" + RESTART_NEEDED_STRING3
    result = parsers.restart_required(input)

    assert (result)


def test_restart_required_negative():
    input = ANY_CLI_OUTPUT
    result = parsers.restart_required(input)

    assert (not result)


def test_reboot_required_with_string1():
    input = ANY_CLI_OUTPUT + "\n" + REBOOT_NEEDED_STRING1
    result = parsers.reboot_required(input)

    assert (result)


def test_reboot_required_negative():
    input = ANY_CLI_OUTPUT
    result = parsers.reboot_required(input)

    assert (not result)


def test_restart_required_with_output_none():
    result = None
    result = parsers.restart_required(result)

    assert (result is False)


def test_empty_output():
    parsed_output = parsers.cli_parse_basic(ANY_EMPTY_OUTPUT)
    assert parsed_output['key'] is None


def test_repeat_output():
    with pytest.raises(KeyError):
        parsers.cli_parse_basic(ANY_REPEAT_OUTPUT)


def test_numerics_output():
    parsed_output = parsers.cli_parse_basic(ANY_NUMERICS_OUTPUT)
    assert parsed_output['key'] == 'string_value'
    assert parsed_output['key2'] == 'numeric 10 with string'
    assert parsed_output['key3'] == 10
    assert type(parsed_output['key3']) is int
    assert parsed_output['key4'] == 10.5
    assert type(parsed_output['key4']) is float
    assert parsed_output['key5'] == '10.5.10.1'


def test_multiple_enabled():
    parsed_output = parsers.cli_parse_basic(ANY_MULTIPLE_ENABLED)
    with pytest.raises(KeyError):
        parsed_output = parsers.enable_squash(parsed_output)


def test_parse_ip_and_port():
    parsed_output = parsers.parse_ip_and_port(IP_PORT_INPUT)
    assert parsed_output == EXPECTED_IP_PORT_INPUT


def test_parse_url_to_host_port_protocol():
    parsed_output = parsers.parse_url_to_host_port_protocol(
        PARSE_URL_TO_HOST_PORT_PROTOCOL_INPUT)
    assert parsed_output == EXPECTED_PARSE_URL_TO_HOST_PORT_PROTOCOL_OUTPUT


def test_parse_saasinfo_data():
    parsed_output = parsers.parse_saasinfo_data(
        PARSE_SAASINFO_DATA_INPUT)
    assert parsed_output == EXPECTED_PARSE_SAASINFO_DATA_OUTPUT


def test_parse_saasinfo_garbage_data():
    with pytest.raises(KeyError):
        parsers.parse_saasinfo_data(
            PARSE_SAASINFO_DATA_GARBAGE_INPUT)
