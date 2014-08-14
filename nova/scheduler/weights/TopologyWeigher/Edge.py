__author__ = 'ash'

from collections import deque
from sys import maxint
import copy

class Edge:

    def __init__(self,node_pair):
        self.node_pair = node_pair


    def init_weights(self):
        """
        Was made because YAML inits only the given fields
        """
        self.bandhist = deque()
        self.histtime = 3600 # keep history for one hour
        self.hist_growed = False
        self.avgbw = 0 # average bandwidth
        self.maxb = -1 # maximum bandwidth
        self.minb = maxint # minimum bandwidth
        self.count = 0

        self.cur_bw_id = -1 # current bandwidth capture period
        self.sim_con_total = 0 # sum of simultaneous (concurrent) connections on this edge
        self.latency = 0

    def calculate_stats(self):
        """
        Re-calculates the statistics
        """
        if self.count == 0: # if it is the first portion of information
            self.avgbw = self.sim_con_total
            self.maxb = self.sim_con_total
            self.minb = self.sim_con_total
            self.count += 1
        else: # we already have first portion
            self.avgbw = (self.avgbw * self.count + self.sim_con_total)  / (self.count + 1) # standard (mean * n + x(i+1))/(n+1)
            self.count += 1
            if self.sim_con_total > self.maxb:
                self.maxb = self.sim_con_total
            if self.sim_con_total < self.minb:
                self.minb = self.sim_con_total

    def append_bandwidth(self,edgeinfo):
        """
        Checking the current traffic sniffing period and calculating the value on the edge
        """
        if edgeinfo.bw_id != self.cur_bw_id: # if new portion of bandwidth statistics
            self.cur_bw_id = edgeinfo.bw_id
            self.calculate_stats() # in sim_con_total - we have accumulated traffic of the previous step. Use it to calc stat
            self.sim_con_total =  edgeinfo.value # the value of first traffic on channel of the new step
        else:
            self.sim_con_total += edgeinfo.value # if the step is the same - accumulating the fraffic on edge

    def __repr__(self):
        return "<Edge: %s : %s" % (self.node_pair,self.sim_con_total)


    @staticmethod
    def edges_list_to_dict(edge_list):
        """
        Get dict from the list as it is more comfortable to work with
        """
        res = dict()
        for edge in edge_list:
            res[(edge.node_pair[0]),(edge.node_pair[1])] = edge
            # Saving the reverse edge for opposite traffic
            edge_reverse = Edge((edge.node_pair[1],edge.node_pair[0]))
            edge_reverse.init_weights()
            res[(edge.node_pair[1]),(edge.node_pair[0])] = edge_reverse
        return res

class EdgeInfo:
    """
    Class describes the portion of traffic information for the bw_id period
    """
    def __init__(self,value,bw_id):
        self.value = value
        #self.time = time
        self.bw_id = bw_id