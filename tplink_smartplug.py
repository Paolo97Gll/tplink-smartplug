#!/usr/bin/env python3
#
# TP-Link Wi-Fi Smart Plug Protocol Client
# For use with TP-Link HS-100 or HS-110
#
# by Lubomir Stroetmann
# Copyright 2016 softScheck GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import argparse
import socket
from struct import pack
from time import sleep
from datetime import datetime
import json
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] (%(levelname)s) %(module)s - %(funcName)s: %(message)s")

version = 0.4,1

# Check if hostname is valid
def validHostname(hostname):
    try:
        socket.gethostbyname(hostname)
    except socket.error:
        parser.error("Invalid hostname.")
    return hostname

# Check if port is valid
def validPort(port):
    try:
        port = int(port)
    except ValueError:
        parser.error("Invalid port number.")
    if ((port <= 1024) or (port > 65535)):
        parser.error("Invalid port number.")
    return port

# Predefined Smart Plug Commands
# For a full list of commands, consult tplink_commands.txt
commands = {'info'     : '{"system":{"get_sysinfo":{}}}',
            'on'       : '{"system":{"set_relay_state":{"state":1}}}',
            'off'      : '{"system":{"set_relay_state":{"state":0}}}',
            'ledoff'   : '{"system":{"set_led_off":{"off":1}}}',
            'ledon'    : '{"system":{"set_led_off":{"off":0}}}',
            'cloudinfo': '{"cnCloud":{"get_info":{}}}',
            'wlanscan' : '{"netif":{"get_scaninfo":{"refresh":0}}}',
            'time'     : '{"time":{"get_time":{}}}',
            'schedule' : '{"schedule":{"get_rules":{}}}',
            'countdown': '{"count_down":{"get_rules":{}}}',
            'antitheft': '{"anti_theft":{"get_rules":{}}}',
            'reboot'   : '{"system":{"reboot":{"delay":1}}}',
            'reset'    : '{"system":{"reset":{"delay":1}}}',
            'energy'   : '{"emeter":{"get_realtime":{}}}'
}

# Encryption and Decryption of TP-Link Smart Home Protocol
# XOR Autokey Cipher with starting key = 171

def encrypt(string):
    key = 171
    result = pack(">I", len(string))
    for i in string:
        a = key ^ ord(i)
        key = a
        result += bytes([a])
    return result

def decrypt(string):
    key = 171
    result = ""
    for i in string:
        a = key ^ i
        key = i
        result += chr(a)
    return result

# Parse commandline arguments
parser = argparse.ArgumentParser(description=f"TP-Link Wi-Fi Smart Plug Client v{version}")
parser.add_argument("-t", "--target", metavar="<hostname>", required=True,
                    help="Target hostname or IP address", type=validHostname)
parser.add_argument("-p", "--port", metavar="<port>", default=9999,
                    required=False, help="Target port", type=validPort)
parser.add_argument("-q", "--quiet", dest="quiet", action="store_true",
                    help="Only show result")
parser.add_argument("--timeout", default=10, required=False,
                    help="Timeout to establish connection")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("-c", "--command", metavar="<command>",
                   help="Preset command to send. Choices are: "+", ".join(commands), choices=commands)
group.add_argument("-j", "--json", metavar="<JSON string>",
                   help="Full JSON string of command to send")
group.add_argument("--keep-time-updated", action="store_true",
                   help="Constantly update the time if needed")
args = parser.parse_args()

# Set target IP, port and command to send
ip = args.target
port = args.port
if args.command is None:
    cmd = args.json
else:
    cmd = commands[args.command]

# Send command and receive reply
def send_command(args, ip, port, cmd):
    try:
        sock_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_tcp.settimeout(int(args.timeout))
        sock_tcp.connect((ip, port))
        sock_tcp.settimeout(None)
        sock_tcp.send(encrypt(cmd))
        data = sock_tcp.recv(2048)
        sock_tcp.close()
        decrypted = decrypt(data[4:])
        return decrypted
    except socket.error:
        logging.error(f"Could not connect to host {ip}:{port}")
        return None

def update_time():
    try:
        rsp = send_command(args, ip, port, commands["time"])
        if rsp:
            rsp = json.loads(rsp)["time"]["get_time"]
            time = datetime.now()
            time_remote = datetime(rsp["year"], rsp["month"], rsp["mday"], rsp["hour"], rsp["min"], rsp["sec"])
            if abs((time_remote - time).total_seconds()) > 60:
                cmd = json.dumps({"time":{"set_timezone":{"year":time.year,"month":time.month,"mday":time.day,"hour":time.hour,"min":time.minute,"sec":time.second,"index":41}}})
                decrypted = send_command(args, ip, port, cmd)
                logging.info(f"Old time: {time_remote}")
                logging.info(f"New time: {time}")
                logging.info(decrypted)
            else:
                logging.info("Time ok, bypass")
        else:
            pass
    except Exception as e:
        logging.exception(e)

# Normal command
if not args.keep_time_updated:
    decrypted = send_command(args, ip, port, cmd)
    if args.quiet:
        logging.info(decrypted)
    else:
        logging.info(f"Sent:     {cmd}")
        logging.info(f"Received: {decrypted}")

# Time updater
else:
    while True:
        update_time()
        sleep(5)
