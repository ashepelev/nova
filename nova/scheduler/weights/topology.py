__author__ = 'ash'

from oslo.config import cfg

from nova.scheduler import weights
from nova.db import api as db_api
from nova.openstack.common import log as logging
import TopologyWeigher.utils as topoutils
from TopologyWeigher.BandwidthHistory import BandwidthHistory as BandwidthHistory
from  TopologyWeigher.Scheduler import Scheduler as Scheduler


topology_weight_opts = [
        cfg.IntOpt('topology_statistics_time',
                   default=3600,
                   help='In seconds. For how many time should the scheduler'
                        'handle the statistics'),
        cfg.IntOpt('channel_max_bandwidth',
                   default=100,
                   help='In Mbits. The bandwidth of the channels in topology'),
        cfg.IntOpt('traffic_multiplier',
                   default=10,
                   help='Multiplies the traffic value to handle with normalizing.'
                        'The more value is - the more scheduler will ignore the disbalance load'
                        'between nodes'),
        cfg.BoolOpt('traffic_enable_topology_statistics',
                   default=False,
                   help='Collect the traffic and ping statistics for scheduling'),
        cfg.StrOpt('topology_description_path',
                   default=None,
                   help='Full path to directory with describing of the topology.'
                        'The directory should have nodes.yaml and edges.yaml files.')
        ]


CONF = cfg.CONF
CONF.register_opts(topology_weight_opts)
LOG = logging.getLogger(__name__)

class TopologyWeighedObject(weights.WeighedHost):
    """
    Implementing new version of WeighedObject
    """
    def __init__(self, obj, weight):
        super(TopologyWeighedObject, self).__init__(obj,weight)

    def set_ip_id(self,ip_addr,id):
        self.obj.ip = ip_addr

    def set_id(self,id):
        self.obj.id = id

    @staticmethod
    def to_weight_list(weighed_obj_list,scheduler_dict,node_by_hostname):
        """
        Transform scheduler answer to nova.scheduler standard type
        :param weighed_obj_list: The input for weigher. Contains the filtered compute-nodes list
        :param scheduler_dict: The weigher work result
        :param node_by_hostname: The dict in format <node hostname>:<node object>
        :return: a list in order of weighed_obj_list contains the weights of the nodes
        """
        weights = []
        for obj in weighed_obj_list:
            weights.append(scheduler_dict[node_by_hostname[obj.obj.host].id])
        print weights
        return weights

class TopologyWeigher(weights.BaseHostWeigher):
    """
    Implementing new version of a Weigher
    """
    minval = 0.0
    maxval = 1.0

    def weight_multiplier(self):
        return -1.0 # as more traffic and latency is worser
    #
    def _weigh_object(self, obj, weight_properties):
        pass

    def weigh_objects(self, weighed_obj_list, weight_properties):
        topology_priority = weight_properties['instance_type'].get('topology_priority',None)
        if topology_priority is None:
            return
        context = weight_properties['context']
        enabled_collector = CONF.traffic_enable_topology_statistics
        topology_path = CONF.topology_description_path

        if not enabled_collector:
            LOG.error("TopologyWeigher won't worked: the traffic collector is disabled in nova.conf")
            return
        if topology_path is None:
            if not topoutils.only_check_db(context):
                LOG.error("TopologyPath doesn't specified in nova.conf and no topology description in db")

        # loading scheduler args of priority
        # loaded from the weigher input - weight_properties

        # Transform the priority input string to the Task object
        task = topoutils.task_from_conf_topopriority(topology_priority)
        # The time before now we need the statistics
        topology_statistics_time = CONF.topology_statistics_time
        # Maximum bandwidth of channels in topology
        # TODO specifiying individual bandwidth for each channel
        max_bandw = CONF.channel_max_bandwidth
        # Multiplier for traffic value
        # The bigger it is - the more scheduler will ignore the compute nodes' resources disbalance
        traf_mult = CONF.traffic_multiplier
        # Get from the db the average traffic for last topology_statistics_time seconds
        traffic_info = db_api.traffic_get_avg(context, topology_statistics_time)
        # Get the topology description information
        (self.node_list,self.edge_list) = topoutils.get_nodes_and_edges(context)
        # Creating the object to aggregate the statistics
        bw_hist_traffic = BandwidthHistory(self.node_list,self.edge_list)
        # Iterate through the traffic load information
        # And aggregate information on the edges
        for tr in traffic_info:
            (val,src,dst) = tr
            src = int(src)
            dst = int(dst)
            # val*8 = value from byte - to bits/s
            # *traf_mult - multiplies - regulates how scheduler will ignore the disbalance load on the nodes
            # max_bandw*1024*1024 = to bit/s
            # /(max_bandw*1024*1024) = normalize based on the maximum bandwidth
            val = (val*8*traf_mult)/(max_bandw*1024*1024)
            bw_hist_traffic.append_traffic((src,dst),val,0)
        # Get the distance matrix, based on the traffic
        dist = Scheduler.build_distances(bw_hist_traffic)
        # Get the dict <hostname>:<node object>
        node_list_by_hostname = topoutils.list_to_endpoints_dict(self.node_list)
        # The weigher works and result the weights of the nodes
        weights = Scheduler.schedule(dist,task,self.node_list)
        # Transforming weigher result to the one accepted by nova.scheduler
        return TopologyWeighedObject.to_weight_list(weighed_obj_list,weights,node_list_by_hostname)







