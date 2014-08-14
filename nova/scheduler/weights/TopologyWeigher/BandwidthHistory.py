from nova.scheduler.weights.TopologyWeigher import Edge, Scheduler

__author__ = 'ash'


class BandwidthHistory:
    """
    Class aggregates the information (metrics) of traffic
    """

    def __init__(self,node_list,edge_list):
        sched = Scheduler.Scheduler(node_list, edge_list)
        # Getting the route matrix (shortest paths)
        self.route_matrix = sched.calc_routes()
        for x in edge_list: # initiate weights with default values
            x.init_weights()
        # Transform to edge dict <(from,to)>:<edge instance>
        self.edge_dict = Edge.Edge.edges_list_to_dict(edge_list)


    def append_traffic(self,pair,value,bw_id):
        """
        Mapping the traffic data of the route to the edges (channels) of the route
        """
        (src,dst) = pair
        route = self.route_matrix[src][dst].route
        ei = Edge.EdgeInfo(value,bw_id)
        # Go through route and setting edge weight
        for i in range(0,len(route)-1): # iterate through route from src to dst
            (v1,v2) = (route[i],route[i+1])
            self.edge_dict[(v1,v2)].append_bandwidth(ei) # accumulate info on the edges

    #TODO implement ping aggregation and usage
    def append_ping(self,pair,value):
        (src, dst) = pair
        route = self.route_matrix[src][dst].route










