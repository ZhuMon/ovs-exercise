# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import in_proto
from ryu.lib.packet import ether_types

from scapy.all import *

FILTER_TABLE = 5
FORWARD_TABLE = 10

class SimpleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.packet_stat = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

        # adding default tables/rules in the startup
        self.add_default_table(datapath)
        self.add_filter_table(datapath)
        self.apply_filter_table_rules(datapath)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None, table=FORWARD_TABLE):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match, table_id=table,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority, table_id=table,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    def add_default_table(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionGotoTable(FILTER_TABLE)]
        mod = parser.OFPFlowMod(datapath=datapath, table_id=0, instructions=inst)
        datapath.send_msg(mod)

    def add_filter_table(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionGotoTable(FORWARD_TABLE)]
        mod = parser.OFPFlowMod(datapath=datapath, table_id=FILTER_TABLE, 
                                priority=1, instructions=inst)
        datapath.send_msg(mod)

    def apply_filter_table_rules(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ip_proto=in_proto.IPPROTO_TCP)
        mod = parser.OFPFlowMod(datapath=datapath, table_id=FILTER_TABLE,
                                priority=10000, match=match)
        datapath.send_msg(mod)



    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch

        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = Ether(msg.data)

        ether_type = ETHER_TYPES[pkt[Ether].type]
        self.packet_stat.setdefault(ether_type, 0)
        self.packet_stat[ether_type] += 1
        if ether_type == 'IPv6':
            ipv6_type = 'IPv6 - ' + ipv6nh[pkt[IPv6].nh]
            self.packet_stat.setdefault(ipv6_type, 0)
            self.packet_stat[ipv6_type] += 1
        elif ether_type == 'IPv4':
            ipv4_type = 'IPv4 - ' + IP_PROTOS[pkt[IP].proto]
            self.packet_stat.setdefault(ipv4_type, 0)
            self.packet_stat[ipv4_type] += 1
            
        elif ether_type == 'LLDP':
            # ignore lldp packet
            return
        dst = pkt[Ether].dst
        src = pkt[Ether].src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        # learn a mac address to avoid FLOOD next time.
        if src not in self.mac_to_port[dpid]:
            self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:

            # check IP Protocol and create a match for IP
            if ether_type == 'IPv4':
                srcip = pkt[IP].src
                dstip = pkt[IP].dst
                match = parser.OFPMatch(eth_type=pkt[Ether].type,
                                        ipv4_src=srcip,
                                        ipv4_dst=dstip
                                        )
            else:
                match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            # verify if we have a valid buffer_id, if yes avoid to send both
            # flow_mod & packet_out
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)


        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
