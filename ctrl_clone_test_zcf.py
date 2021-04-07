
import pd_base_tests

from ptf import config
from ptf.testutils import *
from ptf.thriftutils import *

#from basic_switching.p4_pd_rpc.ttypes import *
#from accounting.p4_pd_rpc.ttypes import *
from clone_test_zcf.p4_pd_rpc.ttypes import *
from res_pd_rpc.ttypes import *
from pltfm_pm_rpc.ttypes import *
from pal_rpc.ttypes import *

from mirror_pd_rpc.ttypes import *


#dev_ports_40g = [139,138]
fp_ports = ["31/2","31/3"]
ports_100G = ["1/0", "3/0", "9/0","11/0","14/0","15/0","16/0","18/0","19/0","20/0","21/0","24/0"]
# loop_fp_port = "5/0"


def convert_to_signed(integer, width):
    max_value = ((1 << (width - 1)) - 1)
    if integer > max_value:
        return -((1 << width) - integer)
    else:
        return integer

def mirror_session(mir_type, mir_dir, sid, egr_port=0, egr_port_v=False,
                   egr_port_queue=0, packet_color=0, mcast_grp_a=0,
                   mcast_grp_a_v=False, mcast_grp_b=0, mcast_grp_b_v=False,
                   max_pkt_len=0, level1_mcast_hash=0, level2_mcast_hash=0,
                   mcast_l1_xid=0, mcast_l2_xid=0, mcast_rid=0, cos=0,
                   c2c=0, extract_len=0, timeout=0, int_hdr=[], hdr_len=0):
      return MirrorSessionInfo_t(mir_type,
                                 mir_dir,
                                 sid,
                                 egr_port,
                                 egr_port_v,
                                 egr_port_queue,
                                 packet_color,
                                 mcast_grp_a,
                                 mcast_grp_a_v,
                                 mcast_grp_b,
                                 mcast_grp_b_v,
                                 max_pkt_len,
                                 level1_mcast_hash,
                                 level2_mcast_hash,
                                 mcast_l1_xid,
                                 mcast_l2_xid,
                                 mcast_rid,
                                 cos,
                                 c2c,
                                 extract_len,
                                 timeout,
                                 int_hdr,
                                 hdr_len)


class L2Test(pd_base_tests.ThriftInterfaceDataPlane):
    def __init__(self):
        pd_base_tests.ThriftInterfaceDataPlane.__init__(self, ["clone_test_zcf"])        ###

    # The setUp() method is used to prepare the test fixture. Typically
    # you would use it to establich connection to the Thrift server.
    #
    # You can also put the initial device configuration there. However,
    # if during this process an error is encountered, it will be considered
    # as a test error (meaning the test is incorrect),
    # rather than a test failure
    def setUp(self):
        pd_base_tests.ThriftInterfaceDataPlane.setUp(self)

        self.sess_hdl = self.conn_mgr.client_init()
        self.dev      = 0
        self.dev_tgt  = DevTarget_t(self.dev, hex_to_i16(0xFFFF))
        self.devPorts = []

        print("\nConnected to Device %d, Session %d" % (
            self.dev, self.sess_hdl))
               


    def configure_ports(self):
        # init ports
        for fpPort in fp_ports:
            port, chnl = fpPort.split("/")
            devPort = self.pal.pal_port_front_panel_port_to_dev_port_get(0, int(port), int(chnl))
            self.devPorts.append(devPort)

        if test_param_get('setup') == True or (test_param_get('setup') != True 
            and test_param_get('cleanup') != True):

            # add and enable the platform ports
            for i in self.devPorts:
                self.pal.pal_port_add(0, i,
                                    pal_port_speed_t.BF_SPEED_10G,
                                    pal_fec_type_t.BF_FEC_TYP_NONE)
                
                self.pal.pal_port_an_set(0, i, 2)       ## in chaofan's tofino, "an-set" is necessary, otherwise some 10G ports are not up
                
                self.pal.pal_port_enable(0, i)
            
        # init ports 100G
        for fpPort in ports_100G:
            port, chnl = fpPort.split("/")
            devPort = self.pal.pal_port_front_panel_port_to_dev_port_get(0, int(port), int(chnl))
            self.devPorts.append(devPort)

        if test_param_get('setup') == True or (test_param_get('setup') != True 
            and test_param_get('cleanup') != True):

            # add and enable the platform ports
            for i in self.devPorts:
                self.pal.pal_port_add(0, i,
                                    pal_port_speed_t.BF_SPEED_100G,
                                    pal_fec_type_t.BF_FEC_TYP_NONE)
                
                self.pal.pal_port_an_set(0, i, 2)       ## in chaofan's tofino, "an-set" is necessary, otherwise some 10G ports are not up
                
                self.pal.pal_port_enable(0, i)
            

            self.conn_mgr.complete_operations(self.sess_hdl)

        print("\nPorts set up successfully.")


    def Populate_mirror_entries(self):
        ttl = 0
        mirror_session = 138
        # # ingress_port_mirror match-action table
        # self.client.ingress_port_mirror_table_add_with_ingress_mirror(
        #     self.sess_hdl, self.dev_tgt,
        #     clone_test_zcf_ingress_port_mirror_match_spec_t(
        #         ipv4_ttl=ttl),
        #     clone_test_zcf_ingress_mirror_action_spec_t(
        #         action_mirror_sess=mirror_session)
        # )
        # print("Table ingress_port_mirror: %d => ingress_mirror(%d)" %
        #       (ttl, mirror_session))
        
        # egress_port_mirror match-action table
        self.client.egress_port_mirror_table_add_with_egress_mirror(
            self.sess_hdl, self.dev_tgt,
            clone_test_zcf_egress_port_mirror_match_spec_t(
                ipv4_ttl=ttl),
            clone_test_zcf_egress_mirror_action_spec_t(
                action_mirror_sess=mirror_session)
        )
        print("Table egress_port_mirror: %d => egress_mirror(%d)" %
              (ttl, mirror_session))

        ttl = 255
        self.client.egress_port_mirror_table_add_with_egress_mirror_remove(
            self.sess_hdl, self.dev_tgt,
            clone_test_zcf_egress_port_mirror_match_spec_t(
                ipv4_ttl=convert_to_signed(ttl, 8))
            )
        print("Table egress_port_mirror: %d => egress_mirror_remove" %
              (ttl))


    def Populate_port_tbl_entries(self):
        
        ingress_port = [139, 148]
        egress_port = [132, 139]
        # ingress_port = [139, 132]
        # egress_port = [148, 139]


        # ingress_port = [139, 148,40]
        # egress_port = [132, 56,139]
        # tmp = ingress_port
        # ingress_port = list(reversed(egress_port))
        # egress_port = list(reversed(tmp))

        # ingress_port = [139, 148,40,0]
        # egress_port = [132, 56,16,139]
        # tmp = ingress_port
        # ingress_port = list(reversed(egress_port))
        # egress_port = list(reversed(tmp))

        hop = 10
        # 4hop
        if hop==4:
            ingress_port = [139, 148,40,0,28]
            egress_port = [132, 56,16,8,139]
            tmp = ingress_port

        # 5hop
        if hop==5:
            ingress_port = [139, 148,40,0,28,20]
            egress_port = [132, 56,16,8,12,139]
            tmp = ingress_port
        
        # 6hop
        if hop==6:
            ingress_port = [139, 148,40,0,28,20,52]
            egress_port = [132, 56,16,8,12,44,139]
            tmp = ingress_port

        # 7hop
        if hop==7:
            ingress_port = [139, 148,40,0,28,20,52,148]
            egress_port = [132, 56,16,8,12,44,132,139]
            tmp = ingress_port

        # 8hop
        if hop==8:
            ingress_port = [139, 148,40,0,28,20,52,148,40]
            egress_port = [132, 56,16,8,12,44,132,56,139]
            tmp = ingress_port

        # 9hop
        if hop==9:
            ingress_port = [139, 148,40,0,28,20,52,148,40,0]
            egress_port = [132, 56,16,8,12,44,132,56,16,139]
            tmp = ingress_port

        # 10hop
        if hop==10:
            ingress_port = [139, 148,40,0,28,20,52,148,40,0,28]
            egress_port = [132, 56,16,8,12,44,132,56,16,8,139]
            tmp = ingress_port
        
        # ingress_port = list(reversed(egress_port))
        # egress_port = list(reversed(tmp))

        print("Populating table entries")

        # port_tbl match-action table
        for i in range(len(ingress_port)):
            self.client.port_tbl_table_add_with_set_md(
                self.sess_hdl, self.dev_tgt,
                clone_test_zcf_port_tbl_match_spec_t(
                    ig_intr_md_ingress_port=ingress_port[i]),
                clone_test_zcf_set_md_action_spec_t(
                    action_eg_port=egress_port[i])
            )
            print("Table port_tbl: %s => set_md(%d)" %
                (ingress_port[i], egress_port[i]))
        
        

        

        

    # This method represents the test itself. Typically you would want to
    # configure the device (e.g. by populating the tables), send some
    # traffic and check the results.
    #
    # For more flexible checks, you can import unittest module and use
    # the provided methods, such as unittest.assertEqual()
    #
    # Do not enclose the code into try/except/finally -- this is done by
    # the framework itself
    def runTest(self):
        
        
        self.configure_ports()
        self.Populate_mirror_entries() 
        self.Populate_port_tbl_entries()  ## python intra-class invoke, write this way.   Only Setup() and runTest() will be executed autoly.


        sids = [128, 138]
        ports = [128, 138]

        for port,sid in zip(ports, sids):
            info = mirror_session(MirrorType_e.PD_MIRROR_TYPE_NORM,
                                    Direction_e.PD_DIR_EGRESS,
                                    sid,
                                    port,
                                    True)
            self.mirror.mirror_session_create(self.sess_hdl, self.dev_tgt, info)
            print "Using session %d for port %d" % (sid, port)
            sys.stdout.flush()
            self.conn_mgr.complete_operations(self.sess_hdl)
        




        