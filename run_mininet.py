import os, sys, json, argparse

from mininet.net import Mininet
from mininet.topo import Topo
from mininet.cli import CLI
from mininet.node import OVSKernelSwitch, Ryu


class MyTopo(Topo):
    def __init__(self, topo_file, **opts):
        Topo.__init__(self, **opts)

        with open(topo_file, 'r') as f:
            topo = json.load(f)


        hosts = topo['hosts']
        switches = topo['switches']
        
        links = self.parse_links(topo['links'])

        host_links = []
        switch_links = []
        self.sw_port_mapping = {}

        for link in links:
            if link['node1'][0] == 'h':
                host_links.append(link)
            else:
                switch_links.append(link)

        link_sort_key = lambda x: x['node1'] + x['node2']

        host_links.sort(key = link_sort_key)
        switch_links.sort(key = link_sort_key)

        for sw in switches:
            self.addSwitch(sw)

        for link in host_links:
            host_name = link['node1']
            host_sw   = link['node2']
            host_num = int(host_name[1:])
            sw_num   = int(host_sw[1:])

            self.addHost(host_name)
            self.addLink(host_name, host_sw)

        for link in switch_links:
            self.addLink(link['node1'], link['node2'])
    
    def parse_links(self, unparsed_links):
        links = []
        for link in unparsed_links:
            s, t = link[0], link[1]
            if s > t:
                s,t = t,s

            link_dict = {'node1': s, 'node2': t}

            if link_dict['node1'][0] == 'h':
                assert link_dict['node2'][0] == 's', 'Hosts should be connected to switches, not ' + str(link_dict['node2'])
            links.append(link_dict)
        return links

def get_args():
    cwd = os.getcwd()
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--topo', help = 'Path to topology json',
                        type=str, required=False, default='./topology.json')

    return parser.parse_args()

if __name__ == "__main__":
    args = get_args()
    topo = MyTopo(args.topo)
    net = Mininet(topo, OVSKernelSwitch, controller=Ryu("Ryu_controller"))
    net.start()
    for h in net.hosts:
        print("**********")
        print(h)
        print("default interface: %s\t%s\t%s" % (h.defaultIntf().name, h.defaultIntf().IP(), h.defaultIntf().MAC()))
        print("**********")

    CLI(net)

    net.stop()
