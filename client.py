0#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import xml.etree.ElementTree as ET
import signal


class XMLMessage(object):
    def __init__(self, command):
        self.command = command
        self.xml_root = ET.Element('Command')
        self.xml_parameters_node = ET.Element('Parameters')
        self.xml_root.append(self.xml_parameters_node)
        self.parameters = []

    def get(self):
        function_name = getattr(self, "init_" + "_".join(self.command.split(" ")) + "_params")
        function_name()

        for parameter in self.parameters:
            node = ET.Element('Parameter')
            node.set('Name', parameter['Name'])
            node.set('Value', parameter['Value'])
            self.xml_parameters_node.append(node)

        return ET.tostring(self.xml_root, 'utf-8')

    def init_login_params(self):
        self.xml_root.set('CommandName', 'Login')
        self.parameters = [{'Name': 'Address', 'Value': '127.0.0.1'},
                           {'Name': 'User', 'Value': 'admin'},
                           {'Name': 'Password', 'Value': 'password'}]

    def init_logout_params(self):
        self.xml_root.set('CommandName', 'Logout')

    def init_discovry_params(self):
        self.xml_root.set('CommandName', 'Discovery')
        self.parameters = [{'Name': 'Address', 'Value': '192.168.42.240/1/1'}]

    def init_bidir_params(self):
        self.xml_root.set('CommandName', 'Bidir')
        self.parameters = [{'Name': 'Port_A', 'Value': '192.168.42.240/1/1'},
                           {'Name': 'Port_B', 'Value': '192.168.42.240/1/2'}]

    def init_unidir_params(self):
        self.xml_root.set('CommandName', 'Unidir')
        self.parameters = [{'Name': 'SrcPort', 'Value': '192.168.42.240/2/1'},
                           {'Name': 'DstPort', 'Value': '192.168.42.240/2/2'}]

    def init_get_attribute_params(self):
        self.xml_root.set('CommandName', 'GetAttributeValue')
        self.parameters = [{'Name': 'Port', 'Value': '192.168.42.240/1/2'},
                           {'Name': 'Attribute', 'Value': 'LIN'}]

    def init_set_attribute_params(self):
        self.xml_root.set('CommandName', 'SetAttributeValue')
        self.parameters = [{'Name': 'Port', 'Value': '192.168.42.240/1/2'},
                           {'Name': 'Attribute', 'Value': 'LIN'},
                           {'Name': 'Value', 'Value': 'ON'}]

sock = socket.socket()
print "Connecting...."
sock.connect(('localhost', 9010))


def close_conn_and_die():
    sock.close()
    print "Good bye ;)"
    exit(0)


def signal_handler(signal, frame):
    print "Interrupted by user, disconnecting...."
    close_conn_and_die()


signal.signal(signal.SIGTSTP, signal_handler)
signal.signal(signal.SIG_IGN, signal_handler)

commandNames = ["login", "logout", "discovry", "bidir", "unidir", "set attribute", "get attribute"]

while True:
    try:
        commandName = raw_input(
            "Type a command to be executed (" + ', '.join(map(str, commandNames)) + " or exit): ")

    except EOFError:
        print "Interrupted by user, disconnecting...."
        close_conn_and_die()

    except KeyboardInterrupt:
        print "Interrupted by user, disconnecting...."
        close_conn_and_die()

    else:
        if commandName == "exit":
            break

        if commandName not in commandNames:
            print "Invalid command"
            continue

        message = XMLMessage(commandName)
        message = message.get()

        print "Sending message...."
        sock.send(message)
        print "Waiting for response...."
        data = sock.recv(1024)
        print data

print "Thank you, disconnecting...."
close_conn_and_die()
