import queue
import threading
from link_3 import LinkFrame

## wrapper class for a queue of packets
class Interface:
    ## @param maxsize - the maximum size of the queue storing packets
    #  @param capacity - the capacity of the link in bps
    def __init__(self, maxsize=0, capacity=500):
        self.in_queue = queue.Queue(maxsize);
        self.out_queue = queue.Queue(maxsize);
        self.capacity = capacity #serialization rate
        self.next_avail_time = 0 #the next time the interface can transmit a packet
    
    ##get packet from the queue interface
    # @param in_or_out - use 'in' or 'out' interface
    def get(self, in_or_out):
        try:
            if in_or_out == 'in':
                pkt_S = self.in_queue.get(False)
                # if pkt_S is not None:
                #   print('getting packet from the IN queue')
                return pkt_S
            else:
                pkt_S = self.out_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the OUT queue')
                return pkt_S
        except queue.Empty:
            return None
        
    ##put the packet into the interface queue
    # @param pkt - Packet to be inserted into the queue
    # @param in_or_out - use 'in' or 'out' interface
    # @param block - if True, block until room in queue, if False may throw queue.Full exception
    def put(self, pkt, in_or_out, block=False):
        if in_or_out == 'out':
            # print('putting packet in the OUT queue')
            self.out_queue.put(pkt, block)
        else:
            # print('putting packet in the IN queue')
            self.in_queue.put(pkt, block)
            
        
## Implements a network layer packet
# NOTE: You will need to extend this class for the packet to include
# the fields necessary for the completion of this assignment.
class NetworkPacket:
    ## packet encoding lengths 
    dst_S_length = 5
    
    ##@param dst: address of the destination host
    # @param data_S: packet payload
    # @param priority: packet priority
    def __init__(self, dst, data_S, priority):
        self.dst = dst
        self.data_S = data_S
        #TODO: add priority to the packet class
        self.priority = priority
        # print("Packet dst: %s" % str(self.dst))
        # print("Packet priority: %s" % str(self.priority))
        # print("Packet data: %s" % str(data_S)+"\n")
        
    ## called when printing the object
    def __str__(self):
        return self.to_byte_S()
        
    ## convert packet to a byte string for transmission over links
    def to_byte_S(self):

        # Initialize the byte string to the priority before adding on the rest
        byte_S = str(self.priority)
        byte_S += str(self.dst).zfill(self.dst_S_length)
        byte_S += self.data_S
        return byte_S
    
    ## extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        priority = byte_S[0: 1]
        destination = byte_S[1: NetworkPacket.dst_S_length+1].strip('0')
        data_S = byte_S[NetworkPacket.dst_S_length+1:]
        return self(destination, data_S, priority)
    

## Implements a network host for receiving and transmitting data
class Host:
    
    ##@param addr: address of this node represented as an integer
    def __init__(self, addr):
        self.addr = addr
        self.intf_L = [Interface()]
        self.stop = False #for thread termination
        #print("Host address: %s" % str(addr), "\nInterface list: %s" % str(self.intf_L), "\nStop @: %s\n" % str(self.stop))
    
    ## called when printing the object
    def __str__(self):
        return self.addr
       
    ## create a packet and enqueue for transmission
    # @param dst: destination address for the packet
    # @param data_S: data being transmitted to the network layer
    # @param priority: packet priority
    def udt_send(self, dst, data_S, priority):
        pkt = NetworkPacket(dst, data_S, priority)
        #print('%s: sending packet "%s" with priority %d' % (self, pkt, priority))
        # encapsulate network packet in a link frame (usually would be done by the OS)
        fr = LinkFrame('Network', pkt.to_byte_S())
        # enque frame onto the interface for transmission
        self.intf_L[0].put(fr.to_byte_S(), 'out') 
        
    ## receive frame from the link layer
    def udt_receive(self):
        fr_S = self.intf_L[0].get('in')
        if fr_S is None:
            return
        # decapsulate the network packet
        fr = LinkFrame.from_byte_S(fr_S)
        assert(fr.type_S == 'Network')  # should be receiving network packets by hosts
        pkt_S = fr.data_S
        # print('%s: received packet "%s"' % (self, pkt_S))
        print("\nHost %s received message: %s" % (str(self), pkt_S))

        return pkt_S
       
    ## thread target for the host to keep receiving data
    def run(self):
        # print (threading.currentThread().getName() + ': Starting')
        while True:
            # receive data arriving to the in interface
            received = self.udt_receive()

            if received is not None:
                # print("Received packet:", str(received))
                pass

            # terminate
            if self.stop:
                #print (threading.currentThread().getName() + ': Ending')
                return


# MPLS class here
class MPLS:
    type = "MPLS"
    class_type = "MPLS"

    def __init__(self, packet, label):
        packet_string = packet.to_byte_S()
        self.label = label
        # Encapsulate the packet_string with an M
        # self.new_packet = "M"+str(label).zfill(2)+packet_string
        self.packet = str(label).zfill(2) + packet_string
        #print("The new packet contains: %s\n\n" % self.packet)

    # returns the MPLS packet contents
    def to_byte_s(self):
        return str(self.packet)

    @classmethod
    def from_byte_s(self, byte_s):
        network_inner_packet = byte_s[2:]
        network_packet = NetworkPacket.from_byte_S(network_inner_packet)
        label = int(byte_s[0:2])
        return self(network_packet, label)


## Implements a multi-interface router
class Router:
    
    ##@param name: friendly router name for debugging
    # @param intf_capacity_L: capacities of outgoing interfaces in bps 
    # @param encap_tbl_D: table used to encapsulate network packets into MPLS frames
    # @param frwd_tbl_D: table used to forward MPLS frames
    # @param decap_tbl_D: table used to decapsulate network packets from MPLS frames
    # @param max_queue_size: max queue length (passed to Interface)
    def __init__(self, name, intf_capacity_L, encap_tbl_D, frwd_tbl_D, decap_tbl_D, max_queue_size):
        self.stop = False  # for thread termination
        self.name = name
        # create a list of interfaces
        self.intf_L = [Interface(max_queue_size, intf_capacity_L[i]) for i in range(len(intf_capacity_L))]
        # save MPLS tables
        self.encap_tbl_D = encap_tbl_D
        self.frwd_tbl_D = frwd_tbl_D
        self.decap_tbl_D = decap_tbl_D
        self.remainingQueue = [0, 0]
        

    ## called when printing the object
    def __str__(self):
        return self.name


    ## look through the content of incoming interfaces and 
    # process data and control packets
    def process_queues(self):
        not_using_priorities = self.getQueuePriorities()
        for i in range(len(self.intf_L)):
            fr_S = None # make sure we are starting the loop with a blank frame
            fr_S = self.intf_L[i].get('in')  # get frame from interface i
            if fr_S is None:
                continue # no frame to process yet
            # decapsulate the packet
            fr = LinkFrame.from_byte_S(fr_S)
            pkt_S = fr.data_S
            # process the packet as network, or MPLS
            if fr.type_S == "Network":
                p = NetworkPacket.from_byte_S(pkt_S) # parse a packet out
                # print("Network queue: " + pkt_S)
                self.process_network_packet(p, i, not_using_priorities)
            elif fr.type_S == "MPLS":
                # TODO: handle MPLS frames
                # print('MPLS QUEUE ' + pkt_S)
                # for now, we just relabel the packet as an MPLS frame without encapsulation
                # Parses a frame out
                mpls_packet = MPLS.from_byte_s(pkt_S)
                # send the MPLS frame for processing
                self.process_MPLS_frame(mpls_packet, i)
            else:
                raise('%s: unknown frame type: %s' % (self, fr.type))

    def getQueuePriorities(self):
        p0 = 0
        p1 = 0
        elements = 0

        for i in range(len(self.intf_L)):
            for element in self.intf_L[i].in_queue.queue:
                if element[0] == 'M':
                    if int(element[3]) == 0:
                        p0 = p0 + 1
                    elif int(element[3]) == 1:
                        p1 = p1 + 1
                else:
                    if int(element[1]) == 0:
                        p0 = p0 + 1
                    elif int(element[1]) == 1:
                        p1 = p1 + 1
                elements += elements + 1
        if p0 != 0 or p1 != 0:
            print('%s: Priority 0 is %s, and Priority 1 is %s' % (str(self), str(p0), str(p1)))
        return p0 + p1 == elements

    ## process a network packet incoming to this router
    #  @param p Packet to forward
    #  @param i Incoming interface number for packet p
    def process_network_packet(self, pkt, i, not_using_priorities):
        # TODO: encapsulate the packet in an MPLS frame based on self.encap_tbl_D
        # for now, we just relabel the packet as an MPLS frame without encapsulation
        # m_fr = pkt
        # print("\nROUTER NAME:", str(self.name))
        # print("pkt.to_byte_s:", str(pkt.to_byte_S()))
        # print("i:", str(i), "\npkt.dst:", str(pkt.dst)+"\n")

        if not_using_priorities:
            out_label = self.encap_tbl_D[i][pkt.dst]
            print('%s: NetworkPacket %s does not have a priority label' % (str(self), str(pkt)))
        else:
            out_label = pkt.priority
            print('%s: NetworkPacket %s has a priority label' % (str(self), str(pkt)))
        m_packet = MPLS(pkt, out_label)
        # print('%s: encapsulated packet "%s" as MPLS frame "%s"' % (self, pkt, m_fr))
        # send the encapsulated packet for processing as MPLS frame
        self.process_MPLS_frame(m_packet, i)

    ## process an MPLS frame incoming to this router
    #  @param m_fr: MPLS frame to process
    #  @param i Incoming interface number for the frame
    def process_MPLS_frame(self, m_fr, i):
        # TODO: implement MPLS forward, or MPLS decapsulation if this is the last hop router for the path
        #print('%s: processing MPLS frame "%s"' % (self, m_fr))
        # for now forward the frame out interface 1
        try:
            # Initalize the output interface to -1
            output_interface = -1
            #checks if we need to decapsulate or not
            if i in self.decap_tbl_D:
                # print("Decapsulating Block;\nRouter name:", str(self.name), "\nString received:", str(m_fr.to_byte_s()))
                priority = m_fr.packet[2: 3]
                dst = m_fr.packet[3:7].strip('0')
                data_S = m_fr.packet[7:]
                fr = LinkFrame('Network', NetworkPacket(dst, data_S, priority).to_byte_S())
                output_interface = self.decap_tbl_D[i][m_fr.label]
            else:
                fr = LinkFrame('MPLS', m_fr.to_byte_s())
                output_interface = self.frwd_tbl_D[int(m_fr.label)]
            self.intf_L[output_interface].put(fr.to_byte_S(), 'out', True)
            # print('%s: forwarding frame "%s" from interface %d to %d' % (self, fr, i, 1))
        except queue.Full:
            # print('%s: frame "%s" lost on interface %d' % (self, m_fr, i))
            pass
        
                
    ## thread target for the host to keep forwarding data
    def run(self):
        # print (threading.currentThread().getName() + ': Starting')
        while True:
            self.process_queues()
            if self.stop:
                # print (threading.currentThread().getName() + ': Ending')
                return 