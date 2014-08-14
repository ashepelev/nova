__author__ = 'ash'

import Node
import Edge
import YamlDoc
from Scheduler import Task
import socket
import fcntl
from struct import *

from nova import db
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
        # As every node is a child of Node.Endpoint
        if isinstance(x,Node.Endpoint):
            node_dict[x.id] = x
    return node_dict

def get_node_dict(node_list):
    """
    Transforms node list to dict <node ip addr>:<node id>
    """
    node_dict = dict()
    for x in node_list:
        # As Switch doesn't have ip addr
        if not isinstance(x, Node.Switch):
            node_dict[x.ip_addr] = x.id
    return node_dict

def get_router_id_ip(node_list):
    """
    Gets the router ip and id
    """
    for x in node_list:
        if isinstance(x, Node.Router):
            return (x.id, x.ip)
    LOG.error("TopologyWeigher: No router found")

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

def get_ip_address(ifname):
    """
    Gets the ip address of the interface
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        pack('256s', ifname[:15])
    )[20:24])

def task_from_conf_topopriority(topology_priority):
    # Constructs a task from the string given at the booting
    # The string came with filter_properties
    priors = topology_priority.split(',')
    prior_list = []
    for prior in priors:
        prior_pare = prior.split(':')
        node = int(prior_pare[0])
        priority = int(prior_pare[1])
        prior_list.append((node,priority))
    return Task(prior_list)

def get_nodes_and_edges(context):
    """
    Gets the description of nodes and edges
    """
    nodes = db.node_get(context)
    edges = db.edge_get(context)
    node_list = []
    edges_list = []
    for node in nodes:
        node_list.append(create_node_from_db(node))
    for edge in edges:
        edges_list.append(create_edge_from_db(edge))
    return (node_list,edges_list)

def create_node_from_db(node):
    """
    Constructs Node objects from the db result
    """
    if node.name == "Switch":
        return Node.Switch(long(node.node_id))
    if node.name == "Router":
        return Node.Router(long(node.node_id),str(node.ip_addr))
    if node.name == "CloudController":
        return Node.CloudController(long(node.node_id),str(node.ip_addr),str(node.hostname))
    if node.name == "ComputeNode":
        return Node.ComputeNode(long(node.node_id),str(node.ip_addr),str(node.hostname))

def create_edge_from_db(edge):
    """
    Construct Edge object from the db result
    """
    return Edge.Edge((int(edge.start),int(edge.end)))

def only_check_db(ctxt):
    node_count = db.check_node(ctxt)
    node_count = int(node_count[0])
    edge_count = db.check_edge(ctxt)
    edge_count = int(edge_count[0])
    return not ((node_count == 0) or (edge_count == 0))

def only_load_db(ctxt, topology_description_path):
    (node_list,edge_list) = get_topology(topology_description_path)
    for node in node_list:
        resources = {}
        resources['node_id'] = node.id
        resources['name'] = get_node_type(node)
        if not isinstance(node, Node.Switch):
            resources['ip_addr'] = node.ip_addr
        if isinstance(node, Node.Endpoint):
            resources['hostname'] = node.hostname
        db.node_add(ctxt, resources)

    for edge in edge_list:
        resources = {}
        resources['start'] = edge.node_pair[0]
        resources['end'] = edge.node_pair[1]
        db.edge_add(ctxt, resources)

def check_and_set_topology(ctxt, topology_description_path):
    """
    After nova-scheduler stated
    If the there is no description of topology in db - it loads
    The topology from local yaml files and load them to db
    """

    node_count = db.check_node(ctxt)
    node_count = int(node_count[0])
    edge_count = db.check_edge(ctxt)
    edge_count = int(edge_count[0])
    if node_count == 0 or edge_count == 0:
        LOG.debug("TopologyWeigher: There is no topology description in db. Loading from local files...")
        (node_list,edge_list) = get_topology(topology_description_path)
    else:
        return

    for node in node_list:
        resources = {}
        resources['node_id'] = node.id
        resources['name'] = get_node_type(node)
        if not isinstance(node, Node.Switch):
            resources['ip_addr'] = node.ip_addr
        if isinstance(node, Node.Endpoint):
            resources['hostname'] = node.hostname
        db.node_add(ctxt, resources)

    for edge in edge_list:
        resources = {}
        resources['start'] = edge.node_pair[0]
        resources['end'] = edge.node_pair[1]
        db.edge_add(ctxt, resources)

def get_node_type(node):
        if isinstance(node,Node.Switch):
            return "Switch"
        if isinstance(node,Node.Router):
            return "Router"
        if isinstance(node,Node.ComputeNode):
            return "ComputeNode"
        if isinstance(node,Node.CloudController):
            return "CloudController"
