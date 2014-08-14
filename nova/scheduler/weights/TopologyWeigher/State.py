__author__ = 'ash'

import random

import Node


class State:

    def __init__(self, node_list, edge_list):
        self.node_list = node_list
        self.edge_list = edge_list

    def setState(self):
        for node in self.node_list:
            if type(node) == Node.ComputeNode:
                node.assign_vcpu(8) # We believe that filters pass #random.randint(0,8))
                node.asiign_ram(16) #random.randint(0,16))

        for edge in self.edge_list:
            edge.assign_avg_bandw(random.randint(0,edge.maxb)) # creating fake load

