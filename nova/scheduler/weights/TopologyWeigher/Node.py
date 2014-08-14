__author__ = 'ash'


class Node:
    """
    Parent for all topology classes
    """

    def __init__(self, vid):
        self.id = vid # characterized only by id

 #   def add_neighbours_by_one(self, n):
 #       self.neighbours.append(n)

 #   def set_neighbours(self, neigh_list):
 #      self.neighbours = neigh_list


class Switch(Node):
    """
    Characterizes only by id.
    """

    def __init__(self, vid):
        self.id = vid

class Router(Node):

    def __init__(self,vid,ip_addr):
        self.id = vid
        self.ip_addr = ip_addr # we add hostname (or can add ip)

    def check_ip(self, ipa):
        octets = ipa.split('.')
        if len(octets) != 4:
            print "IPv4 must have 4 octets"
            return False
        i = 0
        while i < len(octets):
            oc = int(octets[i])
            if oc < 0 or oc > 255:
                print "An octet must be in [0,255]"
                return False
            i+=1
        return True

    def assign_ip(self,ipa):  # to write the ip checker
        if self.check_ip(ipa):
            self.ip_addr = ipa

  #  def add_neighbours(self, n):
  #      if len(self.neighbours > 0):
  #         print "No more than 1 neighbours"
  #          return
  #      self.neighbours.append(n)


class Endpoint(Node):
    """
    Endpoint is the parent class for all service nodes of OpenStack
    """

    def __init__(self,vid,ip_addr,hostname):
        self.id = vid
        self.ip_addr = ip_addr
        self.hostname = hostname


    def assign_ip(self,ipa):
        self.ip_addr = ipa

    def assign_hostname(self, hn):
        self.hostname = hn

class ComputeNode(Endpoint):
    pass

class Storage(Endpoint):
    pass

class NetworkNode(Endpoint):
    pass

class CloudController(Endpoint):
    pass
