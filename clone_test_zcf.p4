#include <tofino/intrinsic_metadata.p4>
#include <tofino/constants.p4>
#include "tofino/stateful_alu_blackbox.p4"

header_type ethernet_t {
    fields {
        dstAddr : 48;
        srcAddr : 48;
        etherType : 16;
    }
}
header ethernet_t ethernet;

header_type ipv4_t {
    fields {
        version        : 4;
        ihl            : 4;
        diffserv       : 8;
        totalLen       : 16;
        identification : 16;
        flags          : 3;
        fragOffset     : 13;
        ttl            : 8;
        protocol       : 8;
        hdrChecksum    : 16;
        srcAddr       : 32;
        dstAddr       : 32;
    }
}
header ipv4_t ipv4;

header_type udp_t {
    fields {
        srcPort : 16;
        dstPort : 16;
        hdr_length : 16;
        checksum : 16;
    }
}
header udp_t udp;

header_type tcp_t {
    fields {
        sPort : 16;
        dPort : 16;
        seqNo : 32;
        ackNo : 32;
        dataOffset : 4;
        res : 3;
        ecn : 3;
        ctrl : 6;
        window : 16;
        checksum : 16;
        urgentPtr : 16;
    }
}
header tcp_t tcp;

header_type mirror_metadata_t {
    fields {
        mirror_type : 1;    // 0-ingress  1-egress
        mirror_sess : 10;
        ingress_port : 9;
    }
}
metadata mirror_metadata_t mirror_meta;  

field_list mirror_list {
    mirror_meta.ingress_port;
    mirror_meta.mirror_sess;
    mirror_meta.mirror_type;
}

header_type ingress_timestamp_t {
    fields {
        ingress_mac_timestamp : 48;
        ingress_global_timestamp : 48;
    }
}
header ingress_timestamp_t ingress_timestamp;

header_type egress_timestamp_t {
    fields {
        egress_global_timestamp : 48;
    }
}
header egress_timestamp_t egress_timestamp;

//////////////////////////////// parser ////////////////////////////////
parser start {
    return parse_ethernet;
}

#define ETHERTYPE_IPV4 0x0800
//#define ETHERTYPE_IPV6 0x86DD
parser parse_ethernet {
    extract(ethernet);
    return select(latest.etherType) {
		//ETHERTYPE_IPV6 : parse_ipv6;
        ETHERTYPE_IPV4 : parse_ipv4;
        default: ingress;
    }
}

#define UDP_PROTO 0x11
#define TCP_PROTO 0x6
parser parse_ipv4 {
    extract(ipv4);
    return select(latest.protocol) {
        UDP_PROTO : parse_udp;
        TCP_PROTO : parse_tcp;
        default : ingress;
    }
}

parser parse_udp {
    extract(udp);
    return select(latest.srcPort) {
        1234 : ingress;                     
        default : parse_ingress_timestamp;  // 后面add_header，前面必须要先有parse该header，，应该也是为了确定它add的位置
    }
}

parser parse_tcp {
    extract(tcp);
    return select(latest.sPort) {
        1234 : ingress;                     
        default : parse_ingress_timestamp;  
    }
}

parser parse_ingress_timestamp {
    extract(ingress_timestamp);
    return parse_egress_timestamp;
}

parser parse_egress_timestamp {
    extract(egress_timestamp);
    return ingress;
}


//////////////////////////////// table ////////////////////////////////

action subtract_ttl_add_header() {
    subtract_from_field(ipv4.ttl, 1);
    add_header(ingress_timestamp);
    modify_field(ingress_timestamp.ingress_mac_timestamp, ig_intr_md.ingress_mac_tstamp);
    modify_field(ingress_timestamp.ingress_global_timestamp, ig_intr_md_from_parser_aux.ingress_global_tstamp);

}
table subtract_ttl_add_header {
    actions {
        subtract_ttl_add_header;
    }
    default_action: subtract_ttl_add_header;
}

action nop(){}
action set_md(eg_port) {
    modify_field(ig_intr_md_for_tm.ucast_egress_port, eg_port);
    //subtract_from_field(ipv4.ttl, 1);

}
table port_tbl {
    reads {
        ig_intr_md.ingress_port : exact;
    }
    actions {
        set_md;
        nop;
    }
    default_action: nop;
    size : 288;
}


action ingress_mirror(mirror_sess){
    modify_field(mirror_meta.mirror_type, 0);
    modify_field(mirror_meta.ingress_port, ig_intr_md.ingress_port);
    modify_field(mirror_meta.mirror_sess, mirror_sess);
    clone_ingress_pkt_to_egress(mirror_sess, mirror_list);
}
table ingress_port_mirror {
    reads {
        ipv4.ttl : exact;
    }
    actions {
        ingress_mirror;
        nop;
    }
    default_action: nop;
}


action egress_mirror(mirror_sess){
    modify_field(mirror_meta.mirror_type, 0);
    modify_field(mirror_meta.ingress_port, ig_intr_md.ingress_port);
    modify_field(mirror_meta.mirror_sess, mirror_sess);
    clone_egress_pkt_to_egress(mirror_sess, mirror_list);

    subtract_from_field(ipv4.ttl, 1); // 防止风暴回环
    
}
action egress_mirror_remove(){
    remove_header(egress_timestamp);
}
table egress_port_mirror {
    reads {
        ipv4.ttl : exact;
    }
    actions {
        egress_mirror;
        egress_mirror_remove;
        nop;
    }
    default_action: nop;
}


// action test_ttl(){
//     add_to_field(ipv4.ttl, 10);
// }
// table test_ttl {
//     actions {
//         test_ttl;
//     }
//     default_action: test_ttl;
// }

action ipv4_forward_egress(){

    add_header(egress_timestamp);
    modify_field(egress_timestamp.egress_global_timestamp, eg_intr_md_from_parser_aux.egress_global_tstamp);

}
table ipv4_forward_egress {
    actions {
        ipv4_forward_egress;
    }
    default_action : ipv4_forward_egress;
}


//////////////////////////////// ingress ////////////////////////////////
control ingress{

    apply(subtract_ttl_add_header);
    if (0 == ig_intr_md.resubmit_flag) {
        apply(port_tbl);
    }

    //apply(ingress_port_mirror);  
    
}

//////////////////////////////// egress ////////////////////////////////
control egress{
    //apply(test_ttl);
    apply(ipv4_forward_egress);

    apply(egress_port_mirror);
}


