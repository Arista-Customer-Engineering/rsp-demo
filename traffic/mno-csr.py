#!/usr/bin/env python3
# --------------------------------------------------------------------
# MNO-CSR traffic generator (cell site router / eNB side)
# src: 172.19.128.120  dst: 172.19.128.121 (MNO-AGG)
#
# Generates toward MNO-AGG:
#   IS-IS  P2P Hello + LSP (IS-IS SR, Ethernet LLC)
#   BGP    OPEN / KEEPALIVE / UPDATE with labeled-unicast NLRI
#          transport labels 900000-965535, VPN label 100000-100099
#   S1-AP  eNB→MME  (SCTP/38412)
#   GTP-C  eNB→SGW  (UDP/2123)  Create/Modify/Delete Session
#   GTP-U  eNB→SGW  (UDP/2152)  nested: IP/MPLS(t)/MPLS(vpn)/IPv6/GTP-U/IPv6
# --------------------------------------------------------------------

import os, sys, random, struct, time, threading
from scapy.all import (
    Ether, LLC, IP, IPv6, UDP, TCP, SCTP, SCTPChunkData,
    Raw, sendp, get_if_hwaddr, conf
)
from scapy.contrib.mpls import MPLS
from scapy.contrib.gtp import GTP_U_Header

try:
    from scapy.contrib.isis import (
        ISIS_CommonHdr, ISIS_P2P_Hello, ISIS_LSP,
        ISIS_AreaTlv, ISIS_IsReachabilityTlv,
    )
    HAS_ISIS = True
except Exception:
    HAS_ISIS = False

try:
    from scapy.contrib.bgp import BGPHeader, BGPOpen, BGPUpdate, BGPKeepAlive
    HAS_BGP = True
except Exception:
    HAS_BGP = False

conf.verb = 0

IFACE      = "eth1.1001"
MY_IP      = "172.19.128.120"
PEER_IP    = "172.19.128.121"
MY_AS      = 65100
PEER_AS    = 65100              # iBGP within MNO

# IS-IS NET: area 49.0001, system-id derived from MY_IP last 3 octets
ISIS_NET   = b'\x49\x00\x01' + b'\x00\x00' + b'\x0a\x13\x80\x78' + b'\x00'
ISIS_SYS_ID = b'\x00\x00\x0a\x13\x80\x78'  # 0a.13.80.78 = 10.19.128.120

# GTP-U target throughput.  Tune this to control data-plane load.
# Batch is 50 pkts × ~1000 B on-wire = ~400 kbits; sleep is derived from that.
GTP_U_KBPS   = 25000                               # target kbps (~25 Mbps)
_BATCH_SIZE  = 50                                  # packets per sendp() call
_BATCH_BITS  = _BATCH_SIZE * 1000 * 8             # bits per batch (approx)
_GTPU_SLEEP  = _BATCH_BITS / (GTP_U_KBPS * 1000)  # seconds between batches

# MPLS label ranges (MNO-internal SR labels)
TRANSPORT_LABEL_MIN = 900000
TRANSPORT_LABEL_MAX = 965535
VPN_LABEL_MIN       = 100000
VPN_LABEL_MAX       = 100099

# GTP-U addresses
BH_SRC_V6  = "2001:db8:mno::120"
BH_DST_V6  = "2001:db8:mno::121"
UE_POOL    = [f"2001:db8:ue::{i:x}" for i in range(1, 64)]
CORE_POOL  = ["2001:db8:core::1", "2001:db8:core::2"]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] [mno-csr] {msg}", flush=True)


# -----------------------------------------------------------------------
# IS-IS
# -----------------------------------------------------------------------

def _isis_frame(pdu_bytes):
    """Wrap IS-IS PDU in Ethernet + LLC (802.2, DSAP/SSAP=0xFE)."""
    return (
        Ether(dst="09:00:2b:00:00:05") /
        LLC(dsap=0xfe, ssap=0xfe, ctrl=3) /
        Raw(pdu_bytes)
    )


def _isis_p2p_iih():
    """Minimal IS-IS P2P IIH (PDU type 17)."""
    if HAS_ISIS:
        pdu = ISIS_CommonHdr(pdutype=17) / ISIS_P2P_Hello(
            circuit_type=3,
            source_id=ISIS_SYS_ID,
            holding_timer=30,
            local_circuit_id=1,
        )
        return bytes(pdu)
    # Manual fallback: CommonHdr(8B) + P2P Hello fixed fields
    hdr = bytes([
        0x83,       # NLPID = IS-IS
        0x14,       # hdr length = 20
        0x01,       # version/proto-id ext = 1
        0x00,       # id length (0 = 6 bytes)
        0x11,       # PDU type = P2P Hello (17)
        0x01,       # version = 1
        0x00,       # reserved
        0x00,       # max area addresses (0 = 3)
    ])
    body = bytes([0x03]) + ISIS_SYS_ID + struct.pack(">H", 30) + bytes([0x01, 0x00])
    length = len(hdr) + len(body)
    hdr = hdr[:8]
    return hdr + body


def _isis_lsp():
    """Minimal IS-IS LSP with SR prefix-SID stub."""
    lsp_id = ISIS_SYS_ID + b'\x00\x00'  # LSP fragment 0
    seq_no = random.randint(1, 0xFFFF)
    # Minimal LSP body: IS-Neighbors TLV (type=2) with one neighbor
    neighbor_tlv = bytes([0x02, 0x07]) + b'\x00' + ISIS_SYS_ID + b'\x00'
    # SR Capability TLV (type=242) stub
    sr_cap_tlv   = bytes([0xf2, 0x06, 0x00,
                          (TRANSPORT_LABEL_MIN >> 12) & 0xFF,
                          (TRANSPORT_LABEL_MIN >> 4)  & 0xFF,
                          ((TRANSPORT_LABEL_MIN & 0xF) << 4) | 0x08,
                          0x00, 0x40])
    body = neighbor_tlv + sr_cap_tlv
    # CommonHdr(8) + fixed(19) + body
    fixed = (lsp_id + struct.pack(">I", seq_no) +
             b'\x00\x00' +   # checksum placeholder
             b'\x00' +       # Type block (P/ATT/OL/IS-type)
             bytes([0x03]))  # IS-type = L1+L2
    hdr = bytes([0x83, 0x1b, 0x01, 0x00, 0x12, 0x01, 0x00, 0x00])
    pdu_len = len(hdr) + len(fixed) + len(body)
    return hdr + struct.pack(">H", pdu_len)[0:1] + fixed[1:] + body


def loop_isis():
    """Send IS-IS P2P IIH every 10 s, LSP every 30 s."""
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
# BGP
# -----------------------------------------------------------------------

def _bgp_open():
    """BGP OPEN: type=1, AS=MY_AS, hold=90, BGP-ID=MY_IP."""
    ip_int = int.from_bytes(bytes(int(x) for x in MY_IP.split(".")), "big")
    # Capabilities: multiprotocol (AFI=1,SAFI=4 labeled unicast) + 4-byte ASN
    mp_cap   = bytes([0x01, 0x04, 0x00, 0x01, 0x00, 0x04])  # MP IPv4 labeled
    as4_cap  = bytes([0x41, 0x04]) + struct.pack(">I", MY_AS)
    caps     = bytes([0x02, len(mp_cap) + len(as4_cap)]) + mp_cap + as4_cap
    opt_params = bytes([0x02, len(caps)]) + caps
    body = struct.pack(">BHI", 4, MY_AS, 90) + struct.pack(">I", ip_int) + bytes([len(opt_params)]) + opt_params
    marker = b'\xff' * 16
    length = 19 + len(body)
    return marker + struct.pack(">HB", length, 1) + body


def _bgp_keepalive():
    return b'\xff' * 16 + struct.pack(">HB", 19, 4)


def _label_nlri(prefix_bytes, prefix_len, label):
    """3-byte MPLS label stack entry + prefix bytes for labeled unicast NLRI."""
    label_stack = struct.pack(">I", (label << 4) | 0x01)[1:]  # 3 bytes, BoS=1
    bits = 24 + prefix_len  # label(24) + prefix length
    return bytes([bits]) + label_stack + prefix_bytes[:((prefix_len + 7) // 8)]


def _bgp_update_labeled(prefixes):
    """
    BGP UPDATE advertising IPv4 labeled unicast (AFI=1, SAFI=4).
    prefixes: list of (prefix_str, prefix_len, label)
    """
    nlri = b""
    for (pfx, plen, lbl) in prefixes:
        pb = bytes(int(x) for x in pfx.split("."))
        nlri += _label_nlri(pb, plen, lbl)
    # MP_REACH_NLRI (type=14): AFI=1, SAFI=4, next-hop=MY_IP, NLRI
    nh = bytes(int(x) for x in MY_IP.split("."))
    mp_attr = bytes([0x00, 0x01, 0x04, 0x04]) + nh + bytes([0x00]) + nlri
    path_attr = bytes([0x90, 0x0e, len(mp_attr)]) + mp_attr
    # ORIGIN igp
    origin = bytes([0x40, 0x01, 0x01, 0x00])
    # LOCAL_PREF 100
    locpref = bytes([0x40, 0x05, 0x04]) + struct.pack(">I", 100)
    attrs = origin + locpref + path_attr
    body = struct.pack(">H", 0) + struct.pack(">H", len(attrs)) + attrs
    marker = b'\xff' * 16
    length = 19 + len(body)
    return marker + struct.pack(">HB", length, 2) + body


def _send_bgp(payload):
    pkt = (Ether() /
           IP(src=MY_IP, dst=PEER_IP) /
           TCP(sport=random.randint(1024, 65535), dport=179, flags="PA") /
           Raw(payload))
    sendp(pkt, iface=IFACE, verbose=False)


def loop_bgp():
    """Send BGP OPEN once, then KEEPALIVE every 30 s and UPDATE every 90 s."""
    _send_bgp(_bgp_open())
    log("BGP OPEN sent")
    cycle = 0
    while True:
        time.sleep(30)
        _send_bgp(_bgp_keepalive())
        if cycle % 3 == 0:
            # Advertise transport prefixes with SR labels
            prefixes = [
                (f"10.{random.randint(0,255)}.{random.randint(0,255)}.0",
                 24,
                 random.randint(TRANSPORT_LABEL_MIN, TRANSPORT_LABEL_MAX))
                for _ in range(4)
            ]
            # Advertise VPN prefix
            prefixes.append(
                ("172.19.128.120", 32, random.randint(VPN_LABEL_MIN, VPN_LABEL_MAX))
            )
            _send_bgp(_bgp_update_labeled(prefixes))
            log(f"BGP UPDATE — {len(prefixes)} labeled prefixes")
        else:
            log("BGP KEEPALIVE")
        cycle += 1


# -----------------------------------------------------------------------
# S1-AP (eNB → MME)  SCTP/38412
# -----------------------------------------------------------------------

S1AP_INITIAL_UE    = bytes([0x00, 0x0C])  # InitialUEMessage
S1AP_CTX_SETUP     = bytes([0x00, 0x09])  # InitialContextSetupRequest
S1AP_PATH_SWITCH   = bytes([0x00, 0x15])  # PathSwitchRequest
S1AP_UE_RELEASE    = bytes([0x00, 0x17])  # UEContextReleaseCommand
S1AP_PAGING        = bytes([0x00, 0x0A])  # Paging


def _s1ap(proc_code):
    return b'\x00' + proc_code + b'\x00' + os.urandom(32)


def _send_s1ap(msg):
    pkt = (Ether() /
           IP(src=MY_IP, dst=PEER_IP) /
           SCTP(sport=38412, dport=38412) /
           SCTPChunkData(data=msg))
    sendp(pkt, iface=IFACE, verbose=False)


def loop_s1ap():
    """Simulate UE attach/handover/release cycles from eNB."""
    batch = 8
    while True:
        log(f"S1-AP: attach batch ({batch} UEs)")
        for _ in range(batch):
            _send_s1ap(_s1ap(S1AP_INITIAL_UE))
            time.sleep(0.05)
            _send_s1ap(_s1ap(S1AP_CTX_SETUP))
            time.sleep(0.05)

        time.sleep(random.randint(60, 180))

        for _ in range(batch // 2):
            _send_s1ap(_s1ap(S1AP_PATH_SWITCH))
            time.sleep(0.1)

        time.sleep(random.randint(30, 90))

        log(f"S1-AP: detach batch ({batch} UEs)")
        for _ in range(batch):
            _send_s1ap(_s1ap(S1AP_UE_RELEASE))
            time.sleep(0.05)

        for _ in range(random.randint(2, 5)):
            _send_s1ap(_s1ap(S1AP_PAGING))

        time.sleep(random.randint(15, 30))


# -----------------------------------------------------------------------
# GTP-C (eNB→SGW)  UDP/2123
# -----------------------------------------------------------------------

_gtpc_seq = 1

def _gtpc_seq_next():
    global _gtpc_seq
    s = _gtpc_seq
    _gtpc_seq = (_gtpc_seq + 1) & 0xFFFFFF
    return s


def _gtpv2(msg_type, teid, body):
    seq = _gtpc_seq_next()
    hdr = struct.pack(">BBHI", 0x48, msg_type, 8 + len(body), teid)
    hdr += struct.pack(">BBBx", (seq >> 16) & 0xFF, (seq >> 8) & 0xFF, seq & 0xFF)
    return hdr + body


def _create_session_req(teid, imsi_s, apn=b"internet"):
    imsi_ie  = struct.pack(">BHB", 0x01, 8, 0x00) + struct.pack(">Q", 0x0001000000000000 | imsi_s)
    apn_enc  = bytes([len(apn)]) + apn
    apn_ie   = struct.pack(">BHB", 0x47, len(apn_enc), 0x00) + apn_enc
    ebi_ie   = struct.pack(">BHBB", 0x49, 1, 0x00, 5)
    bc_ie    = struct.pack(">BHB", 0x5D, len(ebi_ie), 0x00) + ebi_ie
    return _gtpv2(32, teid, imsi_ie + apn_ie + bc_ie)


def _modify_bearer_req(teid):
    ebi_ie = struct.pack(">BHBB", 0x49, 1, 0x00, 5)
    bc_ie  = struct.pack(">BHB", 0x5D, len(ebi_ie), 0x00) + ebi_ie
    return _gtpv2(34, teid, bc_ie)


def _delete_session_req(teid):
    cause_ie = struct.pack(">BHBBx", 0x02, 2, 0x00, 16)
    return _gtpv2(36, teid, cause_ie)


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
    """GTP-C session lifecycle + 60s Echo."""
    echo_counter = 0
    batch = 8
    while True:
        log(f"GTP-C: Create Session batch ({batch})")
        teids = []
        for _ in range(batch):
            teid = random.randint(0x10000000, 0x1FFFFFFF)
            teids.append(teid)
            _send_gtpc(_create_session_req(teid, random.randint(0x100000, 0xFFFFFF)))
            time.sleep(0.05)

        time.sleep(random.randint(60, 180))

        for teid in random.sample(teids, k=max(1, len(teids) // 2)):
            _send_gtpc(_modify_bearer_req(teid))
            time.sleep(0.05)

        time.sleep(random.randint(30, 90))

        log(f"GTP-C: Delete Session batch ({batch})")
        for teid in teids:
            _send_gtpc(_delete_session_req(teid))
            time.sleep(0.05)

        echo_counter += 1
        if echo_counter % 2 == 0:
            _send_gtpc(_gtpc_echo())
            log("GTP-C Echo")

        time.sleep(random.randint(15, 30))


# -----------------------------------------------------------------------
# GTP-U (eNB→SGW)  UDP/2152
# Outer: IP(CSR→AGG) / MPLS(transport,S=0) / MPLS(VPN,S=1) / IPv6 / GTP-U / IPv6(UE)
# -----------------------------------------------------------------------

def _gtp_u_pkt(ue_ip, core_ip, teid, transport_lbl, vpn_lbl, psize=1200):
    inner = (IPv6(src=ue_ip, dst=core_ip) /
             TCP(sport=random.randint(1024, 65535), dport=443, flags="PA") /
             Raw(os.urandom(psize)))
    gtp = GTP_U_Header(teid=teid) / inner
    bh  = IPv6(src=BH_SRC_V6, dst=BH_DST_V6) / UDP(sport=2152, dport=2152) / gtp
    return (Ether(type=0x8847) /
            MPLS(label=transport_lbl, s=0, ttl=64) /
            MPLS(label=vpn_lbl,       s=1, ttl=64) /
            bh)


def loop_gtp_u():
    """GTP-U uplink: ~20 pkt/s across 32 UE sessions."""
    ue_teids = {ue: random.randint(0x10000000, 0x1FFFFFFF) for ue in UE_POOL}
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
            log(f"GTP-U: {pkts_sent} uplink packets sent")
        time.sleep(_GTPU_SLEEP)


# -----------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------

def main():
    log(f"MNO-CSR traffic generator  {MY_IP} → {PEER_IP}")
    log(f"  IS-IS   P2P IIH/LSP (Ethernet LLC)")
    log(f"  BGP     labeled-unicast AS{MY_AS}  labels {TRANSPORT_LABEL_MIN}-{TRANSPORT_LABEL_MAX}")
    log(f"  S1-AP   SCTP/38412")
    log(f"  GTP-C   UDP/2123")
    log(f"  GTP-U   UDP/2152  transport-label/{TRANSPORT_LABEL_MIN}-{TRANSPORT_LABEL_MAX}  vpn-label/{VPN_LABEL_MIN}-{VPN_LABEL_MAX}")

    threads = [
        threading.Thread(target=loop_isis,  daemon=True),
        threading.Thread(target=loop_bgp,   daemon=True),
        threading.Thread(target=loop_s1ap,  daemon=True),
        threading.Thread(target=loop_gtpc,  daemon=True),
        threading.Thread(target=loop_gtp_u, daemon=True),
    ]
    for t in threads:
        t.start()
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
