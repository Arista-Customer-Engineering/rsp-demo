#!/usr/bin/env python3
# --------------------------------------------------------------------
# LTE EPC control-plane traffic simulator
#
# Models traffic between an eNodeB and MME/SGW carried over the SP
# MPLS transport network.
#
# Interfaces simulated:
#
#   S1-AP  eNB → MME   SCTP/38412  UE attach/handover/release
#   GTP-C  MME → SGW   UDP/2123    Create/Modify/Delete Session (S11)
#
# ROLE=enb  → send S1-AP toward MME-IP; receives nothing (one-way sim)
# ROLE=mme  → send GTP-C toward SGW-IP; echoes S1-AP responses back
#
# Run:
#   ROLE=enb MME_IP=10.100.1.2 SGW_IP=10.100.1.2 python3 /epc-signaling.py
#   ROLE=mme ENB_IP=10.100.1.1 SGW_IP=10.100.1.2 python3 /epc-signaling.py
# --------------------------------------------------------------------

import os, sys, time, random, struct, threading
from scapy.all import Ether, IP, UDP, SCTP, SCTPChunkData, Raw, sendp, conf

conf.verb = 0

IFACE   = "eth1"
ROLE    = os.environ.get("ROLE", "enb")
MY_IP   = os.environ.get("MY_IP",  "10.100.1.1" if ROLE == "enb" else "10.100.1.2")
MME_IP  = os.environ.get("MME_IP", "10.100.1.2")
SGW_IP  = os.environ.get("SGW_IP", "10.100.1.2")
ENB_IP  = os.environ.get("ENB_IP", "10.100.1.1")


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] [epc/{ROLE}] {msg}", flush=True)


# -----------------------------------------------------------------------
# GTPv2 (GTP-C) message builders
# Header with TEID (T=1, flags=0x48):
#   Flags(1) | MsgType(1) | Length(2) | TEID(4) | SeqNo(3) | Spare(1)
# Header without TEID (T=0, flags=0x40):
#   Flags(1) | MsgType(1) | Length(2) | SeqNo(3) | Spare(1)
# -----------------------------------------------------------------------

_seq = 1

def _next_seq():
    global _seq
    s = _seq
    _seq = (_seq + 1) & 0xFFFFFF
    return s


def _gtpv2(msg_type, teid, body):
    seq = _next_seq()
    flags = 0x48  # version=2, T=1
    length = 8 + len(body)  # 4B teid + 3B seq + 1B spare + body
    hdr = struct.pack(">BBHI", flags, msg_type, length, teid)
    hdr += struct.pack(">BBBx",
                       (seq >> 16) & 0xFF, (seq >> 8) & 0xFF, seq & 0xFF)
    return hdr + body


def _gtpv2_noteid(msg_type):
    """Echo — no TEID (T=0)."""
    seq = _next_seq()
    flags = 0x40
    body = b""
    length = 4  # 3B seq + 1B spare
    hdr = struct.pack(">BBH", flags, msg_type, length)
    hdr += struct.pack(">BBBx",
                       (seq >> 16) & 0xFF, (seq >> 8) & 0xFF, seq & 0xFF)
    return hdr + body


def create_session_req(teid, imsi_suffix, apn=b"internet"):
    # IMSI IE (type=1, len=8)
    imsi = struct.pack(">Q", 0x0001000000000000 | (imsi_suffix & 0xFFFFFF))
    imsi_ie = struct.pack(">BHB", 0x01, 8, 0x00) + imsi
    # APN IE (type=71)
    apn_enc = bytes([len(apn)]) + apn
    apn_ie  = struct.pack(">BHB", 0x47, len(apn_enc), 0x00) + apn_enc
    # Bearer Context IE (type=93) with EBI IE (type=73, value=5)
    ebi_ie  = struct.pack(">BHBB", 0x49, 1, 0x00, 5)
    bc_ie   = struct.pack(">BHB", 0x5D, len(ebi_ie), 0x00) + ebi_ie
    return _gtpv2(32, teid, imsi_ie + apn_ie + bc_ie)


def create_session_resp(teid, cause=16):
    # Cause IE (type=2, len=2): spare(1) + cause_value(1)
    cause_ie = struct.pack(">BHBBx", 0x02, 2, 0x00, cause)
    return _gtpv2(33, teid, cause_ie)


def modify_bearer_req(teid):
    # Bearer Context stub
    ebi_ie = struct.pack(">BHBB", 0x49, 1, 0x00, 5)
    bc_ie  = struct.pack(">BHB", 0x5D, len(ebi_ie), 0x00) + ebi_ie
    return _gtpv2(34, teid, bc_ie)


def delete_session_req(teid):
    cause_ie = struct.pack(">BHBBx", 0x02, 2, 0x00, 16)
    return _gtpv2(36, teid, cause_ie)


def gtpc_echo():
    return _gtpv2_noteid(1)


def send_gtpc(src, dst, payload):
    pkt = (Ether() /
           IP(src=src, dst=dst) /
           UDP(sport=2123, dport=2123, len=8 + len(payload)) /
           Raw(payload))
    sendp(pkt, iface=IFACE, verbose=False)


# -----------------------------------------------------------------------
# S1-AP message stubs (3GPP TS 36.413)
# Format: ProcedureCode(1) | Criticality(1) | Padding(1) | stub payload
#
# Real S1-AP is ASN.1 PER encoded; these stubs carry the correct
# procedure code bytes so Wireshark labels them correctly.
# -----------------------------------------------------------------------

# InitiatingMessage procedure codes (criticality: 0=reject, 1=ignore, 2=notify)
S1AP_ID_INITIAL_UE        = bytes([0x00, 0x0C])  # InitialUEMessage
S1AP_ID_UE_CTX_SETUP      = bytes([0x00, 0x09])  # InitialContextSetupRequest
S1AP_ID_UE_CTX_RELEASE    = bytes([0x00, 0x17])  # UEContextReleaseCommand
S1AP_ID_PATH_SWITCH       = bytes([0x00, 0x15])  # PathSwitchRequest (handover)
S1AP_ID_ENB_STATUS        = bytes([0x00, 0x1D])  # ENBStatusTransfer
S1AP_ID_PAGING            = bytes([0x00, 0x0A])  # Paging

# Criticality + procedure class prefix for InitiatingMessage
_INITIATING = b'\x00'  # class = initiatingMessage
# Criticality: reject (eNB→MME procedures typically reject on error)
_REJECT = b'\x00'
_IGNORE = b'\x01'


def _s1ap_msg(proc_id_bytes, criticality, payload_size=32):
    """Build a minimal S1-AP PDU: class | procedureCode | criticality | stub."""
    return (_INITIATING + proc_id_bytes + criticality +
            os.urandom(payload_size))


def send_s1ap(src, dst, msg_bytes):
    pkt = (Ether() /
           IP(src=src, dst=dst) /
           SCTP(sport=38412, dport=38412) /
           SCTPChunkData(data=msg_bytes))
    sendp(pkt, iface=IFACE, verbose=False)


# -----------------------------------------------------------------------
# Traffic loops — eNB role
# Drives UE session lifecycle: attach → data → (optional handover) → detach
# -----------------------------------------------------------------------

def enb_ue_lifecycle():
    """Simulate UE attach/detach cycles from the eNB perspective."""
    batch = 8   # UEs per cycle

    while True:
        log(f"UE attach batch ({batch} UEs) → MME {MME_IP}")
        teids = []
        for i in range(batch):
            teid   = random.randint(0x10000000, 0x1FFFFFFF)
            imsi_s = random.randint(0x100000, 0xFFFFFF)
            teids.append(teid)

            # S1-AP: Initial UE Message (UE Attach Request)
            send_s1ap(MY_IP, MME_IP,
                      _s1ap_msg(S1AP_ID_INITIAL_UE, _REJECT, 48))
            time.sleep(0.05)

            # S1-AP: UE Context Setup Request received; send Setup Complete
            # (In real S1-AP, MME sends Setup Req and eNB responds.
            #  Here we send both directions from the eNB node to generate
            #  bidirectional traffic on the fabric link.)
            send_s1ap(MY_IP, MME_IP,
                      _s1ap_msg(S1AP_ID_UE_CTX_SETUP, _REJECT, 64))
            time.sleep(0.05)

        attach_hold = random.randint(60, 180)
        log(f"  {batch} UEs attached — holding {attach_hold}s")
        time.sleep(attach_hold)

        # Random subset hands over
        ho_count = random.randint(1, max(1, batch // 2))
        log(f"  Handover: {ho_count} UEs")
        for _ in range(ho_count):
            send_s1ap(MY_IP, MME_IP,
                      _s1ap_msg(S1AP_ID_PATH_SWITCH, _REJECT, 64))
            time.sleep(0.1)

        time.sleep(random.randint(30, 90))

        # Detach
        log(f"  UE detach batch ({batch} UEs)")
        for _ in range(batch):
            send_s1ap(MY_IP, MME_IP,
                      _s1ap_msg(S1AP_ID_UE_CTX_RELEASE, _IGNORE, 32))
            time.sleep(0.05)

        # Paging bursts (idle UEs being paged)
        for _ in range(random.randint(2, 6)):
            send_s1ap(MY_IP, MME_IP,
                      _s1ap_msg(S1AP_ID_PAGING, _IGNORE, 24))
        time.sleep(random.randint(15, 45))


# -----------------------------------------------------------------------
# Traffic loops — MME role
# Drives GTP-C S11 toward SGW in response to S1-AP attach events.
# Also sends GTP-C Echo keepalives.
# -----------------------------------------------------------------------

def mme_gtpc_sessions():
    """MME→SGW GTP-C S11 session management."""
    batch = 8

    while True:
        log(f"GTP-C S11 Create Session batch ({batch}) → SGW {SGW_IP}")
        teids = []
        for i in range(batch):
            teid   = random.randint(0x20000000, 0x2FFFFFFF)
            imsi_s = random.randint(0x100000, 0xFFFFFF)
            teids.append(teid)

            send_gtpc(MY_IP, SGW_IP, create_session_req(teid, imsi_s))
            time.sleep(0.05)
            # Response (MME receives from SGW; simulate return path)
            send_gtpc(MY_IP, SGW_IP, create_session_resp(teid))
            time.sleep(0.02)

        hold = random.randint(60, 180)
        log(f"  {batch} sessions active — holding {hold}s")
        time.sleep(hold)

        # Handover → Modify Bearer
        for teid in random.sample(teids, k=max(1, len(teids) // 2)):
            send_gtpc(MY_IP, SGW_IP, modify_bearer_req(teid))
            time.sleep(0.05)

        time.sleep(random.randint(30, 90))

        # Detach → Delete Session
        log(f"  GTP-C Delete Session batch ({batch})")
        for teid in teids:
            send_gtpc(MY_IP, SGW_IP, delete_session_req(teid))
            time.sleep(0.05)

        time.sleep(random.randint(15, 45))


def gtpc_echo_keepalive():
    """GTP-C Echo Request every 60 s — standard keepalive on S11."""
    while True:
        send_gtpc(MY_IP, SGW_IP, gtpc_echo())
        log(f"GTP-C Echo → {SGW_IP}")
        time.sleep(60)


# -----------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------

def main():
    log(f"EPC signaling simulator  iface={IFACE}")

    if ROLE == "enb":
        log(f"  S1-AP  {MY_IP}:38412 → MME {MME_IP}:38412 (SCTP)")
        threads = [
            threading.Thread(target=enb_ue_lifecycle, daemon=True),
        ]
    elif ROLE == "mme":
        log(f"  GTP-C  {MY_IP}:2123 → SGW {SGW_IP}:2123 (UDP/S11)")
        threads = [
            threading.Thread(target=mme_gtpc_sessions, daemon=True),
            threading.Thread(target=gtpc_echo_keepalive, daemon=True),
        ]
    else:
        log(f"Unknown ROLE={ROLE}. Set ROLE=enb or ROLE=mme.")
        sys.exit(1)

    for t in threads:
        t.start()

    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
