__author__ = 'ash'

import yaml
import string

class YamlDoc:
    """
    Class for reading the yaml files into topology
    """
    def __init__(self,node_doc,edge_doc):
        stream_nodes = file(node_doc,'r')
        stream_edges = file(edge_doc,'r')
        self.node_list = yaml.load(stream_nodes)
        self.edge_list = yaml.load(stream_edges)
        stream_nodes.close()
        stream_edges.close()

