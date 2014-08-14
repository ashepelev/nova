from TopologyWeigher import utils as topoutils

__author__ = 'ash'

import socket

from struct import *
import pcapy
from time import sleep
from time import time
import shlex
import re
import commands
from subprocess import Popen, PIPE, STDOUT
from threading import Timer
from threading import Thread

from nova.conductor import api as conductor_api
from nova import context
from nova.openstack.common import log as logging
from oslo.config import cfg


traffic_opts = [
        cfg.StrOpt('traffic_sniffing_interface',
                   default=None,
                   help='The interface to listen on for the traffic'),
        cfg.BoolOpt('traffic_enable_topology_statistics',
                   default=False,
                   help='Collect the traffic and ping statistics for scheduling'),
        cfg.IntOpt('refresh_traf_info',
                   default=10,
                   help='In seconds, how often to send traffic statistics to db'),
        cfg.IntOpt('refresh_ping_info',
                   default=10,
                   help='In seconds, how often to send latency statistics to db'),
        cfg.IntOpt('refresh_ping_make',
                   default=5,
                   help='In seconds, how often launch ping for known hosts'),
        cfg.IntOpt('ping_count',
                   default=2,
                   help='How many times during one ping would be sended ICMP echoes')
        ]

CONF = cfg.CONF
CONF.register_opts(traffic_opts)

traffic_stat = dict()
LOG = logging.getLogger("nova-compute")
# Global param - used in ping class
refresh_ping_make = int(CONF.refresh_ping_make)
ping_count = int(CONF.ping_count)

class ClientTraffic(Thread):

    def __init__(self,sniff_int,log):
        Thread.__init__(self)
        # The tread should work as a daemon
        self.daemon = True
        self.error = False
        #self.topology_desc_path = topology_desc_path
        # Get the context for conductor calls
        self.context = context.get_admin_context()
        self.conductor = conductor_api.API()
        # Get the information about the topology from the db
        topoinfo = topoutils.get_nodes(self.context, self.conductor)
        # It might not be in the db - the scheduler have not yet written it
        # Or the scheduler haven't yet started
        if not topoinfo:
            LOG.error("Couldn't get the info about topology")
            self.error = True
            return
        else:
            self.node_list = topoinfo
        # Transforming the node list to dict <ip>:<id>
        self.node_dict = topoutils.get_node_dict(self.node_list)
        # Getting information about the router node id and IP
        (self.router_id,self.router_ip) = topoutils.get_router_id_ip(self.node_list)
        # The interface to listen for the traffic
        self.interface = sniff_int
        # This node's ip_addr
        self.ip_addr = str(topoutils.get_ip_address(str(sniff_int)))
        # Initial value of bw_id
        # TODO: currently doesn't used
        self.bw_id = 0
        # Refresh time of sending the traffic info
        self.refresh_time = int(CONF.refresh_traf_info)
        # Refresh time of sending the ping info
        self.refresh_ping_time = int(CONF.refresh_ping_info)
        # The current node's id
        self.my_id = topoutils.get_my_id(self.node_dict, self.ip_addr)
        self.time_to_send = False
        self.ping_info = dict()
        self.log = log

    def run(self):
        if not self.error:
            self.launch()

    def eth_addr (a) :
        b = "%.2x:%.2x:%.2x:%.2x:%.2x:%.2x" % (ord(a[0]) , ord(a[1]) , ord(a[2]), ord(a[3]), ord(a[4]) , ord(a[5]))
        return b

    def parse_packet(self,packet):
        """
        Function that parses the sniffed packet
        To obtain it's dst/src IPs and it's size
        """

        #parse ethernet header
        eth_length = 14

        eth_header = packet[:eth_length]
        eth = unpack('!6s6sH' , eth_header)
        eth_protocol = socket.ntohs(eth[2])
        #print 'Destination MAC : ' + eth_addr(packet[0:6]) + ' Source MAC : ' + eth_addr(packet[6:12]) + ' Protocol : ' + str(eth_protocol)

        #Parse IP packets, IP Protocol number = 8
        res = False
        if eth_protocol == 8 :
            #Parse IP header
            #take first 20 characters for the ip header
            ip_header = packet[eth_length:20+eth_length]

            #now unpack them :)
            iph = unpack('!BBHHHBBH4s4s' , ip_header)

            version_ihl = iph[0]
            #version = version_ihl >> 4
            ihl = version_ihl & 0xF
            iph_length = ihl * 4

            s_addr = socket.inet_ntoa(iph[8])
            d_addr = socket.inet_ntoa(iph[9])

            protocol = iph[6]
            res = True
            if protocol == 6:
                t = iph_length + eth_length
                tcp_header = packet[t:t+20]

                #now unpack them :)
                tcph = unpack('!HHLLBBHHH' , tcp_header)
                doff_reserved = tcph[4]
                tcph_length = doff_reserved >> 4
                h_size = eth_length + iph_length + tcph_length * 4
                data = packet[h_size:]
                #print 'Version : ' + str(version) + ' IP Header Length : ' + str(ihl) + ' TTL : ' + str(ttl) + ' Protocol : ' + str(protocol) + ' Source Address : ' + str(s_addr) + ' Destination Address : ' + str(d_addr)
                #print ' Source Address : ' + str(s_addr) + ' Destination Address : ' + str(d_addr) + ' Length : ' + str(len(packet))
                return (s_addr,d_addr,len(packet),res)
        return (0,0,0,False)

    def process_ping(self):
        self.send_ping()

    def send_ping(self):
        """
        Function sends ping to db via conductor
        """
        for key in self.ping_info:
            ping = self.ping_info[key]
            # Transforming src/dst IPs to nodes' ids
            (src_id,dst_id) = topoutils.get_hosts_id(ping.src, ping.dst, self.node_dict, self.router_id)
            ping_value = ping.result
            # constructing values for inserting into db
            resources = {}
            resources['src'] = self.my_id
            resources['dst'] = dst_id
            resources['latency'] = ping_value
            self.conductor.ping_add(self.context,resources)


    def handle_new_ips(self,packet):
        """
        Function handles new IPs in src/dst packet
        And creates a new task for ping command
        """
        # Setting dst to be not the same as node's ip_addr
        if packet.src == self.ip_addr:
            dst = packet.dst
        else:
            dst = packet.src
        # If there is no node with that IP
        # We believe that it's an external traffic
        if dst not in self.node_dict:
            dst = self.router_ip
        if not (self.ip_addr,dst) in self.ping_info:
            # Creating the task and starting it
            self.ping_info[self.ip_addr,dst] = ip_ping(self.ip_addr,dst)
            self.ping_info[self.ip_addr,dst].start()

    def handle_packet(self,packet):
        """
        Handles new obtained packet
        """
        self.handle_new_ips(packet)
        # Transforming src/dst IPs to nodes' ids
        (src_id,dst_id) = topoutils.get_hosts_id(packet.src,packet.dst,self.node_dict,self.router_id)
        #print "Packet: Src: " + str(packet.src) + " Dst: " + str(packet.dst)
        # If there is no info about it - saving
        if not (src_id,dst_id) in traffic_stat:
            #self.process_ping(packet)
            nl = NetworkLoad()
            nl.inc(packet.length)
            traffic_stat[(src_id,dst_id)] = nl
        else:
            traffic_stat[(src_id,dst_id)].inc(packet.length)

    def process_bandwidth(self):
        """
        Function calculates the traffic before sending to db
        """
        for k in traffic_stat.keys():
            # (number of bytes in packets sniffed for refresh_time) / refresh_time = bytes/s
            bandwidth = traffic_stat[k].count / self.refresh_time
            (src,dst) = k
            traffic_stat[k].bandwidth = bandwidth

    def send_traffic(self):
        """
        Function sends traffic to db via nova-conductor
        """
        for link in traffic_stat.keys():
            (src_id, dst_id) = link
            bandwidth = traffic_stat[link].bandwidth
            # constructing values for inserting into db
            resources = {}
            resources['src'] = src_id
            resources['dst'] = dst_id
            resources['bytes'] = bandwidth
            resources['m_id'] = self.bw_id
            self.conductor.traffic_add(self.context, resources)
        # the variable that keeps the id number if the measurement
        self.bw_id += 1
        # clearing the history for new portion of data
        traffic_stat.clear()

    def launch(self):
        """
        Main cycle of sniffing the traffic
        """
        # opening pcap on the setted interface
        cap = pcapy.open_live(self.interface,65536,1,0)
        # fix time when we start
        self.start_time = time()
        # Timer that sends ping to db every refresh_ping_time seconds
        rt_ping = RepeatedTimer(self.refresh_ping_time,self.process_ping)
        LOG.debug("Starting traffic collector agent")
        while (1) :
            try:
                (header, packet) = cap.next()
            except: # timeout
                continue
            (src,dst,leng,res) = self.parse_packet(packet)
            if not res:
                #print "Not res"
                continue
            pk = Packet(src,dst,leng)
            self.handle_packet(pk)
            # if the elapsed time is more then refresh_time
            # Send traffic information to db
            if time() - self.start_time > self.refresh_time:
                # reset timer
                self.start_time = time()
                self.process_bandwidth()
                self.send_traffic()

class Packet:
    """
    Class describes the packet info
    """

    def __init__(self, src, dst, length):
        self.src = src
        self.dst = dst
        self.length = length

# Class described the information of load
# between src and dst
# It's instance aggregates the traffic on the route
class NetworkLoad:

    def __init__(self):
        self.count = 0
        self.error = 0
        self.metric_ind = 0
        self.error_ind = 0
        self.metrics = ['B', 'KB', 'MB', 'GB', 'TB']
        self.bandwidth = 0
        self.ping = -1

    def inc(self,leng):
        self.count += leng

    def sum_up(self):
        while self.count >= 1024:
            # error obtaining not significantly TO DO
            self.count /= 1024
            self.metric_ind += 1

class RepeatedTimer(object):
    """
    Help-class for launching timer in a separate thread
    """
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False

class ip_ping(Thread):
    """
    Class to launch ping
    For each new topology node's IP launching an instance of this class
    That pings the node every refresh_ping_make seconds
    """
    def __init__ (self,src,dst):
        Thread.__init__(self)
        self.src = src
        self.dst = dst
        self.result = -1
        self.repeat = refresh_ping_make
        self.count = ping_count

    def run(self):
        p = re.compile('.*time\=([0-9\.]*)\ .*')
        while 1:
            src = self.src
            host = self.dst
            host = host.split(':')[0]
            # if make -c > 1 then need to handle more output
            # better to use fping - but not supported for default on systems
            status, output = commands.getstatusoutput("ping -c {count} {host}".format(count=self.count, host=host))
            lines = output.split('\n')
            avg = 0
            for i in range(1,self.count+1):
                s = p.search(lines[i])
                if s is None:
                    res = 999.0
                    break
                avg += float(s.group(1))
            avg /= self.count
            self.result = avg
            sleep(self.repeat)

    def get_simple_cmd_output(self,cmd, stderr=STDOUT):
        """
        Execute a simple external command and get its output.
        """
        args = shlex.split(cmd)
        return Popen(args, stdout=PIPE, stderr=stderr).communicate()[0]

    def ready(self):
       return self.result != -1

# Checking if the traffic statistics sniffer is enabled
enable_stat = CONF.traffic_enable_topology_statistics
if enable_stat:
    # Getting the interface to listen on
    if CONF.traffic_sniffing_interface is None:
        LOG.error("No traffic_sniffing_interface specified in /etc/nova/nova.conf")
    else:
        interface = str(CONF.traffic_sniffing_interface)
        client = ClientTraffic(interface, LOG)
        client.start()