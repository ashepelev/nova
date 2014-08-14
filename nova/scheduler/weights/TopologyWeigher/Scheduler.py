from nova.scheduler.weights.TopologyWeigher import Node

__author__ = 'ash'

from sets import Set
import sys
#import pulp

class Task:

    def __init__(self,vm_dep_list):
        self.vm_dep_list = vm_dep_list

    @staticmethod
    def example_task():
        vm_dep_list = [(2,20)] # list of dependencies. format: (<compute_node_id>,<priority>)
        #storage_priority = 4
        #public_priority = 4
        task = Task(vm_dep_list,1,1)
        return task

class Scheduler:

    def __init__(self,node_list,edges_list):
        self.node_list = node_list
        self.edge_list = edges_list
        self.dim = len(node_list)
        self.infinity = 10000
        self.undefined = -1

    def make_adjacency_matrix(self):
        """
        Initiating the empty adjacency_matrix
        """
        matrix = [[self.infinity for x in xrange(self.dim)] for y in xrange(self.dim)]
        for edge in self.edge_list:
            i,j = edge.node_pair
            test = matrix[i][j]
            # Set that there is a way from i to j
            matrix[i][j] = int(1)
            matrix[j][i] = int(1)
        return matrix

    def min_distance(self,dist,q):
        """
        Finds in dist minimal distance with indexes from the queue q
        """
        min = sys.maxint
        minind = -1
        for elem in q:
            if (dist[elem] < min):
                min = dist[elem]
                minind = elem
        return minind

    def dijkstra(self,matrix,src):
        """
        Standard Dijkstra algorithm. For source finds shortest pathes to every other node.
        """
        dist = [self.infinity for x in xrange(self.dim)]
        previous = [self.undefined for x in xrange(self.dim)]
        route_list = [[] for x in xrange(self.dim)]
        dist[src] = 0
        q = Set()
        for i in range(0,self.dim):
            q.add(i)
        while (len(q) > 0):
            if (len(q) == self.dim):
                u = src
            else:
                u = self.min_distance(dist,q)
            q.remove(u)

            target = u
            path_node = u
            while previous[path_node] != self.undefined:
                route_list[target].append(path_node)
                path_node = previous[path_node]
            route_list[target].append(src)
            route_list[target].reverse() # as we aggregate it reverse

            for j in range(0,self.dim):
                if j == u:
                    continue
                alt = dist[u] + matrix[u][j]
                if alt < dist[j]:
                    dist[j] = alt
                    previous[j] = u

        return (dist,route_list)

    def calc_routes(self):
        """
        With dijkstra algorithm builds the route matrix in the whole topology
        """
        matrix = self.make_adjacency_matrix()
        route_matrix = []
        for i in range(0,self.dim):
            (dist, route_list) = self.dijkstra(matrix,i)
            route_matrix.append([])
            for j in range(0,self.dim):
                rt = Route(dist[j],route_list[j])
                route_matrix[i].append(rt)
        return route_matrix

    @staticmethod
    def build_distances(bw_hist):
        """
        Takes the information about the weights on edges
        and builds the matrix of distances between nodes.
        """
        route_matrix = bw_hist.route_matrix
        edge_dict = bw_hist.edge_dict
        dim = len(route_matrix)
        dist = [[0 for x in range(0,dim)] for y in range(0,dim)]
        for i in range(0,dim):
            for j in range(0,dim):
                route = route_matrix[i][j].route
                route_sum = 0
                for k in range(0,len(route)-1):
                    (v1,v2) = (route[k],route[k+1])
                    route_sum += edge_dict[(v1,v2)].sim_con_total
                dist[i][j] = route_sum
        return dist

    @staticmethod
    def schedule(dist,task,node_list):
        """
        Simple scheduler. For every appropriate node (Compute node)
        finds the max the prior nodes
        """
        priorities = task.vm_dep_list
        min_dist = sys.maxint
        min_glob = sys.maxint
        min_id = -1
        weight_list = {}
        # Go through acceptable nodes
        for node in node_list:
            if not isinstance(node, Node.ComputeNode):
                continue
            max_route = 0
            # Go through the priority list
            for prior in priorities:
                # Summing the traffic backward and forward the priority node
                traf = dist[node.id][prior[0]]*prior[1] + dist[prior[0]][node.id]*prior[1]
                if traf > max_route: # We are searching for maximum traffic on route link
                    max_route = traf
            weight_list[node.id] = max_route
        return weight_list

    def print_route(self, route_matrix):
        for i in range(0,self.dim):
            for j in range(0,self.dim):
                sys.stdout.write("From " + str(i) + " to " + str(j) + " dist " + str(route_matrix[i][j].dist) + " Route: ")
                print route_matrix[i][j].route

class Route:

    def __init__(self,dist,route):
        self.dist = dist
        self.route = route

    def __repr__(self):
        return "<Route: %s Distance: %s" % (self.route, self.dist)


