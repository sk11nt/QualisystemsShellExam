#!/usr/bin/env python
# coding: utf-8

import socket
import xml.etree.ElementTree as ET
import time
from platform import system as system_name # Returns the system/OS name
from os import system as system_call       # Execute a shell command


class ServerRequest(object):
    def __init__(self, xml_string):
        self.requestTime = time.time()
        self.xml = ET.fromstring(xml_string)
        self.command = self.xml.get('CommandName')
        self.command_args = {}

    def execute(self):
        self.parse_args()
        function_name = getattr(self, "execute_" + self.command.lower())
        function_name()

    def parse_args(self):
        parameters = self.xml.find('Parameters')
        if parameters is not None:
            for parameter in parameters.findall('Parameter'):
                self.command_args[parameter.get('Name')] = parameter.get('Value')

    def check_auth_expired(self):
        return (self.requestTime - lastAuthTime) < 10*60

    def execute_login(self):
        global authenticatedState, lastAuthTime

        if authenticatedState and self.check_auth_expired():
            return 1

        ping_parameters = "-n 1" if system_name().lower() == "windows" else "-c 1"
        ping_res = system_call("ping " + ping_parameters + " " + self.command_args.get("Address")) == 0
        if not ping_res:
            time.sleep(60)
            ping_res = system_call("ping " + ping_parameters + " " + self.command_args.get("Address")) == 0

        if ping_res:
            authenticatedState = True
            lastAuthTime = self.requestTime

        return int(ping_res)


data = '<Command CommandName="Login"><Parameters><Parameter Name="Address" Value="127.0.0.1" /><Parameter Name="User" Value="admin" /><Parameter Name="Password" Value="password" /></Parameters></Command>'

lastAuthTime = 0
authenticatedState = False


ServerRequest(data).execute()
time.sleep(10)
ServerRequest(data).execute()

exit(0)

sock = socket.socket()
sock.bind(('', 9010))
sock.listen(1)
conn, addr = sock.accept()

print 'connected:', addr

while True:
    data = conn.recv()
    if not data:
        break

    # try:
    #     ServerRequest(data)
    conn.sendall(data)

conn.close()
