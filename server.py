#!/usr/bin/env python
# coding: utf-8

import socket
import xml.etree.ElementTree as ET
import time
from platform import system as system_name  # Returns the system/OS name
from os import system as system_call        # Execute a shell command
import hashlib
import json


class ServerRequest(object):
    def __init__(self, xml_string):
        self.requestTime = time.time()
        self.xml = ET.fromstring(xml_string)
        self.command = self.xml.get('CommandName')
        self.command_args = {}
        self.response = {"Success": 0}

    def execute(self):
        self.parse_args()
        function_name = getattr(self, "execute_" + self.command.lower())
        function_name()

        return self.response

    def parse_args(self):
        parameters = self.xml.find('Parameters')
        if parameters is not None:
            for parameter in parameters.findall('Parameter'):
                self.command_args[parameter.get('Name')] = parameter.get('Value')

    def check_auth(self):
        global lastAuthTime, authenticatedState
        return authenticatedState and (self.requestTime - lastAuthTime) < 10*60

    @staticmethod
    def ping_host(host):
        ping_parameters = "-n 1" if system_name().lower() == "windows" else "-c 1"
        return system_call("ping " + ping_parameters + " " + host) == 0

    def execute_login(self):
        global authenticatedState, lastAuthTime

        if self.check_auth():
            self.response["Success"] = 1
            return

        ping_response = self.ping_host(self.command_args.get("Address"))
        if not ping_response:
            time.sleep(60)
            ping_response = self.ping_host(self.command_args.get("Address"))
        if ping_response:
            authenticatedState = True
            lastAuthTime = self.requestTime

        self.response["Success"] = int(ping_response)

    def execute_logout(self):
        global authenticatedState

        self.response["Success"] = int(self.check_auth())
        authenticatedState = False

    @staticmethod
    def add_address_to_discovery_list(address, address_hash):
        global discovery_list

        if address_hash not in discovery_list.keys():
            address_parts = address.split("/")
            discovery_list[address_hash] = {
                "ip": address_parts[0],
                "ip_blade": address_parts[0]+"/"+address_parts[1],
                "ip_blade_port": address
            }

    def execute_bidir(self):
        global bidir_port_pairs_hashes, bidir_port_hashes, discovery_list

        if not self.check_auth():
            self.response["Log"] = "Not logged in"
            return

        port_a = self.command_args.get("Port_A")
        port_b = self.command_args.get("Port_B")
        port_a_md5_hash = hashlib.md5(port_a).hexdigest()
        port_b_md5_hash = hashlib.md5(port_b).hexdigest()

        self.add_address_to_discovery_list(port_a, port_a_md5_hash)
        self.add_address_to_discovery_list(port_b, port_b_md5_hash)

        port_a_is_new = True
        port_b_is_new = True
        port_pair_is_new = True

        if port_a_md5_hash in bidir_port_hashes:
            port_a_is_new = False
        else:
            bidir_port_hashes.append(port_a_md5_hash)

        if port_b_md5_hash in bidir_port_hashes:
            port_b_is_new = False
        else:
            bidir_port_hashes.append(port_b_md5_hash)

        if not port_a_is_new and not port_b_is_new:

            if port_a_md5_hash + port_b_md5_hash in bidir_port_pairs_hashes:
                port_pair_is_new = False
            else:
                bidir_port_pairs_hashes.append(port_a_md5_hash + port_b_md5_hash)

            if port_b_md5_hash + port_a_md5_hash in bidir_port_pairs_hashes:
                port_pair_is_new = False
            else:
                bidir_port_pairs_hashes.append(port_b_md5_hash + port_a_md5_hash)

        if not port_pair_is_new:
            self.response["Success"] = 1
            self.response["ResponseInfo"] = "CONNECTION EXISTS"
        else:
            if not port_a_is_new or not port_b_is_new:
                self.response["Success"] = 1
                self.response["ResponseInfo"] = "CONNECTION USED"
            else:
                self.response["Success"] = 1
                self.response["ResponseInfo"] = "CONNECTION CREATED"

    def execute_unidir(self):
        global discovery_list, unidir_src_port_hashes, unidir_dst_port_hashes, unidir_port_pairs_hashes

        if not self.check_auth():
            self.response["Log"] = "Not logged in"
            return

        port_src = self.command_args.get("SrcPort")
        port_dst = self.command_args.get("DstPort")
        port_src_md5_hash = hashlib.md5(port_src).hexdigest()
        port_dst_md5_hash = hashlib.md5(port_dst).hexdigest()

        self.add_address_to_discovery_list(port_src, port_dst_md5_hash)
        self.add_address_to_discovery_list(port_dst, port_dst_md5_hash)

        port_src_is_new = False
        port_dst_is_new = False
        port_pair_is_new = False
        port_pair_is_opposite = False

        if port_src_md5_hash not in unidir_src_port_hashes:
            unidir_src_port_hashes.append(port_src_md5_hash)
            port_src_is_new = True
        if port_dst_md5_hash not in unidir_dst_port_hashes:
            unidir_dst_port_hashes.append(port_dst_md5_hash)
            port_dst_is_new = True
        if port_dst_md5_hash+port_src_md5_hash in unidir_port_pairs_hashes:
            port_pair_is_opposite = True
        if port_src_md5_hash+port_dst_md5_hash not in unidir_port_pairs_hashes:
            unidir_port_pairs_hashes.append(port_src_md5_hash+port_dst_md5_hash)
            port_pair_is_new = True

        if not port_pair_is_new:
            self.response["ResponseInfo"] = "CONNECTION EXISTS"
            self.response["Success"] = 1
            return
        else:
            if port_pair_is_opposite:
                self.response["ResponseInfo"] = "CONNECTION CREATED"
                self.response["Success"] = 1
                return
            else:
                if not port_src_is_new:
                    self.response["ResponseInfo"] = "SrcPORT is USED - Creating additional connection"
                    self.response["Success"] = 1
                    return
                if not port_dst_is_new:
                    self.response["ResponseInfo"] = "DstPORT is USED - Not creating an additional connection"
                    self.response["Success"] = 1
                    return

        self.response["Log"] = "Both ports are new, response is not specified =/"

    def execute_discovery(self):
        global discovery_list

        if not self.check_auth():
            self.response["Log"] = "Not logged in"
            return

        address = self.command_args.get("Address")
        self.add_address_to_discovery_list(address, hashlib.md5(address).hexdigest())
        self.response["Success"] = 1

    def execute_setattributevalue(self):
        global port_attributes

        if not self.check_auth():
            self.response["Log"] = "Not logged in"
            return

        port = self.command_args.get("Port")
        attribute_name = self.command_args.get("Attribute")
        attribute_value = self.command_args.get("Value")

        port_hash = hashlib.md5(port).hexdigest()
        if port_hash not in port_attributes.keys():
            port_attributes[port_hash] = {}
        port_attributes[port_hash][attribute_name] = attribute_value

        self.response["Success"] = 1

    def execute_getattributevalue(self):
        global port_attributes

        if not self.check_auth():
            self.response["Log"] = "Not logged in"
            return

        port = self.command_args.get("Port")
        attribute_name = self.command_args.get("Attribute")

        port_hash = hashlib.md5(port).hexdigest()
        if port_hash not in port_attributes.keys():
            self.response["Log"] = "No port found"
            return
        if attribute_name not in port_attributes[port_hash].keys():
            self.response["Log"] = "No attribute found"
            return

        self.response["Success"] = 1
        self.response["Value"] = port_attributes[port_hash][attribute_name]


lastAuthTime = 0
authenticatedState = False
bidir_port_hashes = []
bidir_port_pairs_hashes = []
discovery_list = {}
unidir_src_port_hashes = []
unidir_dst_port_hashes = []
unidir_port_pairs_hashes = []
port_attributes = {}

# data = '<Command CommandName="Bidir"><Parameters><Parameter Name="Port_A" Value="192.168.42.240/1/1"/><Parameter Name="Port_B" Value="192.168.42.240/1/2"/></Parameters></Command>'
#
# ServerRequest(data).execute()
# exit(0)
# time.sleep(10)
# ServerRequest(data).execute()

# exit(0)

sock = socket.socket()
sock.bind(('', 9010))
sock.listen(1)
conn, addr = sock.accept()

print 'connected:', addr

while True:
    data = conn.recv(1024)
    if not data:
        break

    response = ServerRequest(data).execute()
    conn.sendall(json.dumps(response))

conn.close()
