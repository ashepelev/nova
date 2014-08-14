__author__ = 'ash'

import Node
import YamlDoc
import socket
import fcntl
from struct import *
from time import sleep

from nova.openstack.common import log as logging

LOG = logging.getLogger(__name__)

def get_topology(path=None,nodes_file = "nodes.yaml", edges_file = "edges.yaml"):
    """
    Gets the information about topology from the .yaml files
    :param path: directory path
    :param nodes_file: Not-strict yaml file with nodes
    :param edges_file: Not-strict yaml file with edges
    :return: pair with node list and edge list
    """
    if path==None:
        LOG.error("No topology path specified for TopologyWeigher")
        return
    n_path = path + "/"
    yd = YamlDoc.YamlDoc(n_path + nodes_file,n_path+edges_file)
    return (yd.node_list,yd.edge_list)

def list_to_endpoints_dict(node_list):
    """
    Transforms node list to dict <hostname>:<node object>
    """
    node_dict = {}
    for x in node_list:
        if isinstance(x,Node.ComputeNode):
            node_dict[x.hostname] = x
    return node_dict

def get_node_dict_by_id(node_list):
    """
    Transforms node list to dict <node_id>:<node object>
    """
    node_dict = dict()
    for x in node_list:
        if isinstance(x,Node.Endpoint):
            node_dict[x.id] = x
    return node_dict

def get_node_dict(node_list):
    """
    Transforms node list to dict <node ip addr>:<node id>
    """
    node_dict = dict()
    for x in node_list:
        if not isinstance(x, Node.Switch):
            node_dict[x.ip_addr] = x.id
    return node_dict

def get_router_id_ip(node_list):
    """
    Gets the router ip and id
    """
    for x in node_list:
        if isinstance(x, Node.Router):
            return (x.id, x.ip_addr)
    LOG.error("Traffic-Monitor: No router found")

def get_hosts_id(src_ip,dst_ip,node_dict,router_id):
    """
    Transforms packet's src/dst IPs to node's ids
    Checking if src or dst IP is external
    """
    if src_ip not in node_dict:
        src_id = router_id
    else:
        src_id = node_dict[src_ip]
    if dst_ip not in node_dict:
        dst_id = router_id
    else:
        dst_id = node_dict[dst_ip]
    return (src_id,dst_id)

def get_my_id(node_dict,my_ip):
    """
    Returns id of this node
    """
    return node_dict[my_ip]

def get_ip_address(if_name):
    """
    Gets the ip address of the interface
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        pack('256s', if_name[:15])
    )[20:24])

def cycle_conductor_call(func,args):
    """
    Hack function for conductor calls.
    Tries to call function each second until done
    """
    while 1:
        try:
            result = func(args)
            return result
        except: # Obviosly remote error - NoSuchMethod - the magic or RPC to not work sometimes
            sleep(1)

def cycle_conductor_add(func,context,values):
    """
    Hack function for conductor calls.
    Tries to call function each second until done
    """
    while 1:
        try:
            result = func(context,values)
            return result
        except: # Obviosly remote error - NoSuchMethod - the magic or RPC to not work sometimes
            sleep(1)

def get_nodes(context,api):
    """
    Function gets topology description via nova-conductor
    :param context: security context
    :param api: conductor API
    :return: node list
    """
    # Get the count of the nodes in db
    node_count = api.check_node(context)#cycle_conductor_call(api.check_node,context)
    node_count = int(node_count[0])
    if node_count == 0: # scheduler haven't yet started and didn't set the db tables with topology info
        sleep(5)        # we will wait some time
        node_count = api.check_node(context)#cycle_conductor_call(api.check_node,context)
        node_count = int(node_count[0])
    # That means that the scheduler haven't started
    # Possible case - launching this service standalone
    if node_count == 0:
        LOG.error("Traffic statistics cannot be launched: there is no info about topology in db. Check that nova-scheduler is launched")
        return False
    nodes = api.node_get(context)#cycle_conductor_call(api.node_get,context)
    node_list = []
    for node in nodes:
        node_list.append(create_node_from_db(node))
    return node_list

def create_node_from_db(node):
    """
    Based on the data from db construct instances of Node classes
    """
    if node['name'] == "Switch":
        return Node.Switch(int(node['node_id']))
    if node['name'] == "Router":
        return Node.Router(int(node['node_id']),str(node['ip_addr']))
    if node['name'] == "CloudController":
        return Node.CloudController(int(node['node_id']),str(node['ip_addr']),str(node['hostname']))
    if node['name'] == "ComputeNode":
        return Node.ComputeNode(int(node['node_id']),str(node['ip_addr']),str(node['hostname']))
