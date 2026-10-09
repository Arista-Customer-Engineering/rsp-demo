#!/usr/bin/env python3
# --------------------------------------------------------------------
# Mobile backhaul traffic simulator
#
# Generates packets that simulate a mobile operator's backhaul traffic
# carried over the SP MPLS fabric as an L2VPN pseudowire.
#
# Packet stack (from outer to inner):
#   Ethernet
#   └─ Dot1Q (VLAN 100 — mobile operator's access VLAN)
#      └─ IP (RAN site → Mobile core, routed across SP fabric)
#         └─ MPLS label 1000 (transport, S=0)
#            └─ MPLS label 2000 (VPN/service, S=1)
#               └─ IPv6 (backhaul transport addresses)
#                  └─ UDP/2152 (GTP-U well-known port)
#                     └─ GTP-U (TEID per bearer/session)
#                        └─ IPv6 (UE address, inner payload)
#                           └─ TCP/443 or UDP (simulated user data)
#
# Run from a node with eth1 connected to the SP fabric:
#   python3 /mobile-backhaul.py
#
# Requires: scapy (included in ghcr.io/nicolaka/netshoot)
# --------------------------------------------------------------------

from scapy.all import Ether, Dot1Q, IP, MPLS, IPv6, UDP, TCP, Raw, sendp, conf
from scapy.contrib.gtp import GTP_U_Header
import time
import random
import sys
import os

IFACE         = "eth1"

# Outer IP addresses — RAN site and mobile core facing the SP fabric.
# These should align with whatever the SP assigns as PE-to-PE IPs
# for the L2VPN/pseudowire service.
RAN_IP        = "10.100.1.1"     # This node's IP
CORE_IP       = "10.100.2.1"     # Far-end mobile core IP

# 802.1Q — mobile operator's internal VLAN inside the pseudowire
VLAN_ID       = 100

# MPLS label stack — mobile operator's own SR/MPLS within the PW payload
# In a real deployment these would be allocated by the MNO's own control plane.
# For demo purposes any non-reserved values work; choose something visually
# distinct from the SP's own labels (which EOS allocates from 16–1048575).
MPLS_TRANSPORT = 1000   # outer label — "transport" in MNO network, S=0
MPLS_VPN       = 2000   # inner label — VPN/service label,           S=1

# GTP-U port (3GPP TS 29.281)
GTP_PORT      = 2152

# IPv6 backhaul transport block (link between RAN and core inside MPLS VPN)
BH_SRC_V6     = "2001:db8:100::1"   # RAN transport address
BH_DST_V6     = "2001:db8:200::1"   # Core transport address

# UE address pools (simulated mobile subscribers)
UE_SRC_POOL   = [f"2001:db8:cafe::{i:x}" for i in range(1, 64)]
UE_DST_POOL   = ["2001:db8:babe::1", "2001:db8:babe::2", "2001:db8:babe::3"]

# Traffic profiles: (name, proto, dport, payload_range_bytes)
PROFILES = [
    ("VoLTE",        "UDP",  5004,  172),   # G.711 AMR 12.2 kbps, 20ms frame
    ("VoLTE",        "UDP",  5004,  172),   # weight it higher
    ("eMBB-stream",  "TCP",  443,   1400),  # 4G/5G bulk user data
    ("eMBB-stream",  "TCP",  443,   1400),
    ("eMBB-web",     "TCP",  80,    512),   # HTTP/browser traffic
    ("IoT-upload",   "UDP",  8080,  64),    # small IoT sensor frames
    ("eMBB-video",   "TCP",  443,   1400),  # video streaming
]


def build_pkt(src_ue: str, dst_ue: str, teid: int, profile: tuple) -> bytes:
    """Build one mobile backhaul packet for the given UE session."""
    name, proto, dport, psize = profile

    sport = random.randint(1024, 65535)
    if proto == "UDP":
        inner = IPv6(src=src_ue, dst=dst_ue) / \
                UDP(sport=sport, dport=dport) / \
                Raw(os.urandom(psize))
    else:
        inner = IPv6(src=src_ue, dst=dst_ue) / \
                TCP(sport=sport, dport=dport, flags="PA") / \
                Raw(os.urandom(psize))

    gtp = GTP_U_Header(teid=teid, length=len(bytes(inner))) / inner

    bh_transport = IPv6(src=BH_SRC_V6, dst=BH_DST_V6) / \
                   UDP(sport=GTP_PORT, dport=GTP_PORT) / \
                   gtp

    mpls_stack = MPLS(label=MPLS_TRANSPORT, cos=0, s=0, ttl=64) / \
                 MPLS(label=MPLS_VPN,       cos=0, s=1, ttl=64) / \
                 bh_transport

    return Ether() / \
           Dot1Q(vlan=VLAN_ID, type=0x0800) / \
           IP(src=RAN_IP, dst=CORE_IP, proto=137, ttl=64) / \
           mpls_stack


def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [mobile-bh] {msg}", flush=True)


def main():
    conf.verb = 0  # suppress scapy sendp noise

    log(f"Starting mobile backhaul simulation on {IFACE}")
    log(f"Stack: Eth / Dot1Q({VLAN_ID}) / IP / "
        f"MPLS({MPLS_TRANSPORT},S=0) / MPLS({MPLS_VPN},S=1) / "
        f"IPv6 / UDP({GTP_PORT}) / GTP-U / IPv6(UE)")
    log(f"Simulating {len(UE_SRC_POOL)} UEs across {len(PROFILES)} traffic profiles")

    # Assign a stable TEID per UE (real systems use bearer setup signalling)
    ue_teids = {ue: random.randint(0x10000000, 0x1FFFFFFF) for ue in UE_SRC_POOL}

    batch_size = 20     # packets per send burst
    interval   = 0.05  # seconds between bursts ≈ 400 pkt/s

    pkts_sent = 0
    while True:
        batch = []
        for _ in range(batch_size):
            src_ue  = random.choice(UE_SRC_POOL)
            dst_ue  = random.choice(UE_DST_POOL)
            teid    = ue_teids[src_ue]
            profile = random.choice(PROFILES)
            batch.append(build_pkt(src_ue, dst_ue, teid, profile))

        sendp(batch, iface=IFACE, inter=0, verbose=False)
        pkts_sent += len(batch)

        if pkts_sent % 1000 == 0:
            log(f"{pkts_sent} packets sent")

        time.sleep(interval)


if __name__ == "__main__":
    main()
