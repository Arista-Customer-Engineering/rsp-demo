#!/usr/bin/env python3
# --------------------------------------------------------------------
# MNO-AGG traffic generator (aggregation router / MME+SGW side)
# src: 172.19.128.121  dst: 172.19.128.120 (MNO-CSR)
#
# Generates toward MNO-CSR:
#   IS-IS  P2P Hello + LSP (reverse adjacency)
#   BGP    KEEPALIVE / UPDATE (return routes with labeled unicast)
#   GTP-C  MME→SGW S11  Create Session Response + Echo
#   GTP-U  SGW→eNB downlink  IP/MPLS(t)/MPLS(vpn)/IPv6/GTP-U/IPv6
# --------------------------------------------------------------------

import os, sys, random, struct, time, threading
from scapy.all import (
    Ether, LLC, IP, IPv6, UDP, TCP, SCTP, SCTPChunkData,
    Raw, sendp, conf
)
from scapy.contrib.mpls import MPLS
from scapy.contrib.gtp import GTP_U_Header

try:
    from scapy.contrib.isis import ISIS_CommonHdr, ISIS_P2P_Hello, ISIS_LSP
    HAS_ISIS = True
except Exception:
    HAS_ISIS = False

conf.verb = 0

IFACE      = "eth1.1001"
MY_IP      = "172.19.128.121"
PEER_IP    = "172.19.128.120"
MY_AS      = 65100
PEER_AS    = 65100

ISIS_SYS_ID = b'\x00\x00\x0a\x13\x80\x79'   # 10.19.128.121

# GTP-U target throughput.  Tune this to control data-plane load.
GTP_U_KBPS   = 25000                               # target kbps (~25 Mbps)
_BATCH_SIZE  = 50                                  # packets per sendp() call
_BATCH_BITS  = _BATCH_SIZE * 1000 * 8
_GTPU_SLEEP  = _BATCH_BITS / (GTP_U_KBPS * 1000)

TRANSPORT_LABEL_MIN = 900000
TRANSPORT_LABEL_MAX = 965535
VPN_LABEL_MIN       = 100000
VPN_LABEL_MAX       = 100099

BH_SRC_V6  = "2001:db8:mno::121"
BH_DST_V6  = "2001:db8:mno::120"
UE_POOL    = [f"2001:db8:ue::{i:x}" for i in range(1, 64)]
CORE_POOL  = ["2001:db8:core::1", "2001:db8:core::2"]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] [mno-agg] {msg}", flush=True)


# -----------------------------------------------------------------------
# IS-IS  (mirror of CSR side — AGG responds with its own IIH/LSP)
# -----------------------------------------------------------------------

def _isis_frame(pdu):
    return (
        Ether(dst="09:00:2b:00:00:05") /
        LLC(dsap=0xfe, ssap=0xfe, ctrl=3) /
        Raw(pdu)
    )


def _isis_p2p_iih():
    hdr = bytes([0x83, 0x14, 0x01, 0x00, 0x11, 0x01, 0x00, 0x00])
    body = bytes([0x03]) + ISIS_SYS_ID + struct.pack(">H", 30) + bytes([0x01, 0x00])
    return hdr + body


def _isis_lsp():
    lsp_id  = ISIS_SYS_ID + b'\x00\x00'
    seq_no  = random.randint(1, 0xFFFF)
    nb_tlv  = bytes([0x02, 0x07]) + b'\x00' + ISIS_SYS_ID + b'\x00'
    sr_cap  = bytes([0xf2, 0x06, 0x00,
                     (TRANSPORT_LABEL_MIN >> 12) & 0xFF,
                     (TRANSPORT_LABEL_MIN >> 4)  & 0xFF,
                     ((TRANSPORT_LABEL_MIN & 0xF) << 4) | 0x08,
                     0x00, 0x40])
    body    = nb_tlv + sr_cap
    fixed   = lsp_id + struct.pack(">I", seq_no) + b'\x00\x00\x00\x03'
    hdr     = bytes([0x83, 0x1b, 0x01, 0x00, 0x12, 0x01, 0x00, 0x00])
    pdu_len = len(hdr) + len(fixed) + len(body)
    return hdr + struct.pack(">H", pdu_len)[0:1] + fixed[1:] + body


def loop_isis():
    cycle = 0
    while True:
        sendp(_isis_frame(_isis_p2p_iih()), iface=IFACE, verbose=False)
        if cycle % 3 == 0:
            sendp(_isis_frame(_isis_lsp()), iface=IFACE, verbose=False)
            log("IS-IS LSP sent")
        else:
            log("IS-IS P2P IIH sent")
        cycle += 1
        time.sleep(10)


# -----------------------------------------------------------------------
# BGP  (AGG side: OPEN + KEEPALIVE + UPDATE with return routes)
# -----------------------------------------------------------------------

def _bgp_open():
    ip_int = int.from_bytes(bytes(int(x) for x in MY_IP.split(".")), "big")
    mp_cap   = bytes([0x01, 0x04, 0x00, 0x01, 0x00, 0x04])
    as4_cap  = bytes([0x41, 0x04]) + struct.pack(">I", MY_AS)
    caps     = bytes([0x02, len(mp_cap) + len(as4_cap)]) + mp_cap + as4_cap
    opt_params = bytes([0x02, len(caps)]) + caps
    body = (struct.pack(">BHI", 4, MY_AS, 90) +
            struct.pack(">I", ip_int) +
            bytes([len(opt_params)]) + opt_params)
    marker = b'\xff' * 16
    return marker + struct.pack(">HB", 19 + len(body), 1) + body


def _bgp_keepalive():
    return b'\xff' * 16 + struct.pack(">HB", 19, 4)


def _label_nlri(prefix_bytes, prefix_len, label):
    label_stack = struct.pack(">I", (label << 4) | 0x01)[1:]
    bits = 24 + prefix_len
    return bytes([bits]) + label_stack + prefix_bytes[:((prefix_len + 7) // 8)]


def _bgp_update_labeled(prefixes):
    nlri = b""
    for (pfx, plen, lbl) in prefixes:
        pb = bytes(int(x) for x in pfx.split("."))
        nlri += _label_nlri(pb, plen, lbl)
    nh     = bytes(int(x) for x in MY_IP.split("."))
    mp_attr = bytes([0x00, 0x01, 0x04, 0x04]) + nh + bytes([0x00]) + nlri
    path_attr = bytes([0x90, 0x0e, len(mp_attr)]) + mp_attr
    origin    = bytes([0x40, 0x01, 0x01, 0x00])
    locpref   = bytes([0x40, 0x05, 0x04]) + struct.pack(">I", 100)
    attrs = origin + locpref + path_attr
    body  = struct.pack(">H", 0) + struct.pack(">H", len(attrs)) + attrs
    marker = b'\xff' * 16
    return marker + struct.pack(">HB", 19 + len(body), 2) + body


def _send_bgp(payload):
    pkt = (Ether() /
           IP(src=MY_IP, dst=PEER_IP) /
           TCP(sport=random.randint(1024, 65535), dport=179, flags="PA") /
           Raw(payload))
    sendp(pkt, iface=IFACE, verbose=False)


def loop_bgp():
    _send_bgp(_bgp_open())
    log("BGP OPEN sent")
    # Stagger relative to CSR to simulate natural iBGP exchange
    time.sleep(5)
    cycle = 0
    while True:
        time.sleep(30)
        _send_bgp(_bgp_keepalive())
        if cycle % 3 == 0:
            prefixes = [
                (f"10.{random.randint(0,255)}.{random.randint(0,255)}.0",
                 24,
                 random.randint(TRANSPORT_LABEL_MIN, TRANSPORT_LABEL_MAX))
                for _ in range(4)
            ]
            # AGG advertises its own loopback (172.19.128.121) as VPN endpoint
            prefixes.append(
                ("172.19.128.121", 32, random.randint(VPN_LABEL_MIN, VPN_LABEL_MAX))
            )
            _send_bgp(_bgp_update_labeled(prefixes))
            log(f"BGP UPDATE — {len(prefixes)} labeled prefixes")
        else:
            log("BGP KEEPALIVE")
        cycle += 1


# -----------------------------------------------------------------------
# GTP-C  (AGG side: Create Session Response + Echo)  UDP/2123
# -----------------------------------------------------------------------

_gtpc_seq = 0x800000  # start offset from CSR to avoid collision

def _gtpc_seq_next():
    global _gtpc_seq
    s = _gtpc_seq
    _gtpc_seq = (_gtpc_seq + 1) & 0xFFFFFF
    return s


def _gtpv2_resp(msg_type, teid, body):
    seq = _gtpc_seq_next()
    hdr = struct.pack(">BBHI", 0x48, msg_type, 8 + len(body), teid)
    hdr += struct.pack(">BBBx", (seq >> 16) & 0xFF, (seq >> 8) & 0xFF, seq & 0xFF)
    return hdr + body


def _create_session_resp(teid, cause=16):
    cause_ie = struct.pack(">BHBBx", 0x02, 2, 0x00, cause)
    return _gtpv2_resp(33, teid, cause_ie)


def _modify_bearer_resp(teid):
    cause_ie = struct.pack(">BHBBx", 0x02, 2, 0x00, 16)
    return _gtpv2_resp(35, teid, cause_ie)


def _delete_session_resp(teid):
    cause_ie = struct.pack(">BHBBx", 0x02, 2, 0x00, 16)
    return _gtpv2_resp(37, teid, cause_ie)


def _gtpc_echo():
    seq = _gtpc_seq_next()
    hdr = struct.pack(">BBH", 0x40, 1, 4)
    hdr += struct.pack(">BBBx", (seq >> 16) & 0xFF, (seq >> 8) & 0xFF, seq & 0xFF)
    return hdr


def _send_gtpc(payload):
    pkt = (Ether() /
           IP(src=MY_IP, dst=PEER_IP) /
           UDP(sport=2123, dport=2123, len=8 + len(payload)) /
           Raw(payload))
    sendp(pkt, iface=IFACE, verbose=False)


def loop_gtpc():
    """AGG drives S11 GTP-C lifecycle from MME/SGW perspective."""
    batch = 8
    while True:
        log(f"GTP-C: Create Session Response batch ({batch})")
        teids = []
        for _ in range(batch):
            teid = random.randint(0x20000000, 0x2FFFFFFF)
            teids.append(teid)
            _send_gtpc(_create_session_resp(teid))
            time.sleep(0.05)

        time.sleep(random.randint(60, 180))

        for teid in random.sample(teids, k=max(1, len(teids) // 2)):
            _send_gtpc(_modify_bearer_resp(teid))
            time.sleep(0.05)

        time.sleep(random.randint(30, 90))

        log(f"GTP-C: Delete Session Response batch ({batch})")
        for teid in teids:
            _send_gtpc(_delete_session_resp(teid))
            time.sleep(0.05)

        _send_gtpc(_gtpc_echo())
        log("GTP-C Echo")
        time.sleep(random.randint(15, 30))


# -----------------------------------------------------------------------
# GTP-U downlink (SGW→eNB)  UDP/2152
# Outer: IP(AGG→CSR) / MPLS(transport,S=0) / MPLS(VPN,S=1) / IPv6 / GTP-U / IPv6(UE)
# -----------------------------------------------------------------------

def _gtp_u_pkt(ue_ip, core_ip, teid, transport_lbl, vpn_lbl, psize=800):
    inner = (IPv6(src=core_ip, dst=ue_ip) /
             TCP(sport=443, dport=random.randint(1024, 65535), flags="PA") /
             Raw(os.urandom(psize)))
    gtp = GTP_U_Header(teid=teid) / inner
    bh  = IPv6(src=BH_SRC_V6, dst=BH_DST_V6) / UDP(sport=2152, dport=2152) / gtp
    return (Ether(type=0x8847) /
            MPLS(label=transport_lbl, s=0, ttl=64) /
            MPLS(label=vpn_lbl,       s=1, ttl=64) /
            bh)


def loop_gtp_u():
    """GTP-U downlink toward eNB."""
    ue_teids = {ue: random.randint(0x30000000, 0x3FFFFFFF) for ue in UE_POOL}
    t_lbl = random.randint(TRANSPORT_LABEL_MIN, TRANSPORT_LABEL_MAX)
    v_lbl = random.randint(VPN_LABEL_MIN, VPN_LABEL_MAX)
    log(f"GTP-U labels: transport={t_lbl}  vpn={v_lbl}")
    pkts_sent = 0
    while True:
        batch = []
        for _ in range(_BATCH_SIZE):
            ue  = random.choice(UE_POOL)
            cor = random.choice(CORE_POOL)
            batch.append(_gtp_u_pkt(ue, cor, ue_teids[ue], t_lbl, v_lbl,
                                    random.randint(200, 1400)))
        sendp(batch, iface=IFACE, inter=0, verbose=False)
        pkts_sent += len(batch)
        if pkts_sent % 500 == 0:
            log(f"GTP-U: {pkts_sent} downlink packets sent")
        time.sleep(_GTPU_SLEEP)


# -----------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------

def main():
    log(f"MNO-AGG traffic generator  {MY_IP} → {PEER_IP}")
    log(f"  IS-IS   P2P IIH/LSP (Ethernet LLC)")
    log(f"  BGP     labeled-unicast AS{MY_AS}  labels {TRANSPORT_LABEL_MIN}-{TRANSPORT_LABEL_MAX}")
    log(f"  GTP-C   UDP/2123 (responses + Echo)")
    log(f"  GTP-U   UDP/2152 downlink")

    threads = [
        threading.Thread(target=loop_isis,  daemon=True),
        threading.Thread(target=loop_bgp,   daemon=True),
        threading.Thread(target=loop_gtpc,  daemon=True),
        threading.Thread(target=loop_gtp_u, daemon=True),
    ]
    for t in threads:
        t.start()
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
