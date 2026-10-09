#!/usr/bin/env python3
"""
add_dhcpv6_pd_sync.py

For each SVI in AVD network-services that has DHCPv6 relay with prefix-delegation:
  1. Identifies which PE nodes host that SVI (via endpoints_pon_shelves)
  2. Resolves each peer PE's p2p (underlay) IP from core_interfaces
  3. Patches group_vars/mpls/fabric.yml — adds raw_eos_cli to each affected node:
       dhcp relay
          ipv6 routes sync neighbor <peer-p2p-ip>
     so that DHCP-installed PD routes are synced across all anycast-GW partners

Uses ruamel.yaml to preserve existing comments and formatting.
Multiline strings are written as block scalars (|).

Usage:
    ~/.venv/avd-6.0/bin/python add_dhcpv6_pd_sync.py [--inventory PATH] [--dry-run]
"""
import argparse
import ipaddress
import io
import sys
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString

INVENTORY_DEFAULT = Path(__file__).parent / "inventories"
PD_MARKER = "ipv6 dhcp relay install routes prefix-delegation"


# ---------------------------------------------------------------------------
# YAML helpers (ruamel — comment + formatting preserving)
# ---------------------------------------------------------------------------

def make_yaml() -> YAML:
    y = YAML()
    y.preserve_quotes = True
    y.width = 120
    y.best_sequence_indent = 2
    y.best_map_flow_style = False
    return y


def load_yaml(path: Path) -> object:
    if not path.exists():
        return {}
    y = make_yaml()
    with open(path) as f:
        return y.load(f) or {}


def save_yaml(path: Path, data: object, dry_run: bool = False) -> None:
    y = make_yaml()
    buf = io.StringIO()
    y.dump(data, buf)
    content = buf.getvalue()
    if dry_run:
        print(f"\n{'='*60}\nDRY-RUN — would write: {path}\n{'='*60}\n{content}")
    else:
        path.write_text(content)
        print(f"  Written: {path}")


def literal(s: str) -> LiteralScalarString:
    """Wrap a string so ruamel emits it as a block scalar (|)."""
    return LiteralScalarString(s)


# ---------------------------------------------------------------------------
# Step 1 — find SVI profiles that install PD relay routes
# ---------------------------------------------------------------------------

def find_pd_profiles(svi_profiles: list) -> set:
    return {
        p["profile"]
        for p in svi_profiles
        if PD_MARKER in p.get("raw_eos_cli", "")
    }


# ---------------------------------------------------------------------------
# Step 2 — map SVI IDs → PE nodes via endpoints subinterface VLAN IDs
# ---------------------------------------------------------------------------

def vlan_to_nodes_from_endpoints(endpoints_file: Path) -> dict[int, list[str]]:
    vlan_nodes: dict[int, list[str]] = {}
    for endpoints_list in load_yaml(endpoints_file).values():
        for shelf in endpoints_list:
            for adapter in shelf.get("adapters", []):
                switches = list(adapter.get("switches", []))
                for sub in adapter.get("port_channel", {}).get("subinterfaces", []):
                    vlan_id = sub.get("vlan_id")
                    if vlan_id is not None:
                        vlan_nodes.setdefault(int(vlan_id), []).extend(switches)
    return vlan_nodes


def svi_to_pe_nodes(
    services_dir: Path,
    endpoints_file: Path,
    pd_profiles: set,
) -> dict[int, list[str]]:
    """Return {svi_id: [node, ...]} for anycast SVIs using a PD relay profile."""
    vlan_nodes = vlan_to_nodes_from_endpoints(endpoints_file)
    svi_pe_map: dict[int, list[str]] = {}

    for f in sorted(services_dir.glob("services_*.yml")):
        data = load_yaml(f)
        for tenants in data.values():
            if not isinstance(tenants, list):
                continue
            for tenant in tenants:
                for vrf in tenant.get("vrfs", []):
                    for svi in vrf.get("svis", []):
                        svi_id = svi.get("id")
                        profile = svi.get("profile", "")
                        has_anycast = bool(
                            svi.get("ip_address_virtual")
                            or svi.get("ipv6_address_virtuals")
                        )
                        if profile in pd_profiles and has_anycast and svi_id in vlan_nodes:
                            svi_pe_map[int(svi_id)] = vlan_nodes[int(svi_id)]

    return svi_pe_map


# ---------------------------------------------------------------------------
# Step 3 — resolve p2p IPs from core_interfaces
# ---------------------------------------------------------------------------

def build_p2p_ip_map(p2p_links: list, ip_pools: list, profiles: list) -> dict[str, list[str]]:
    """
    Allocate /31 subnets sequentially from each pool (sorted by link id).
    Returns {node_name: [ip, ...]} — the p2p address on that node's interface.

    AVD allocates the n-th /31 subnet of the pool to the n-th link that uses
    that pool (sorted by link id).  nodes[0] gets subnet[0], nodes[1] gets subnet[1].
    """
    pools: dict[str, ipaddress.IPv4Network] = {
        p["name"]: ipaddress.IPv4Network(p["ipv4_pool"]) for p in ip_pools
    }

    profile_pool: dict[str, str] = {
        p["name"]: p["ip_pool"] for p in profiles if "ip_pool" in p
    }

    pool_subnets: dict[str, list] = {
        name: list(net.subnets(new_prefix=31)) for name, net in pools.items()
    }

    pool_idx: dict[str, int] = {name: 0 for name in pools}
    node_ips: dict[str, list[str]] = {}

    for link in sorted(p2p_links, key=lambda l: l.get("id", 0)):
        profile_name = link.get("profile")
        pool_name = profile_pool.get(profile_name)

        if pool_name is None:
            continue
        if pool_name not in pool_subnets:
            print(f"  Warning: pool '{pool_name}' not found, skipping link id={link.get('id')}")
            continue

        subnets = pool_subnets[pool_name]
        idx = pool_idx[pool_name]
        if idx >= len(subnets):
            print(f"  Warning: pool '{pool_name}' exhausted at link id={link.get('id')}")
            continue

        subnet = subnets[idx]
        pool_idx[pool_name] = idx + 1

        addrs = list(subnet)  # /31: both addresses usable per RFC 3021
        nodes = list(link.get("nodes", []))
        if len(nodes) >= 1:
            node_ips.setdefault(str(nodes[0]), []).append(str(addrs[0]))
        if len(nodes) >= 2:
            node_ips.setdefault(str(nodes[1]), []).append(str(addrs[1]))

    return node_ips


# ---------------------------------------------------------------------------
# Step 4 — generate and patch fabric.yml node entries
# ---------------------------------------------------------------------------

def dhcp_relay_cli_block(peer_ips: list[str]) -> LiteralScalarString:
    """Return the EOS CLI block as a ruamel LiteralScalarString (block scalar)."""
    lines = ["dhcp relay"]
    for ip in sorted(peer_ips):
        lines.append(f"   ipv6 routes sync neighbor {ip}")
    return literal("\n".join(lines) + "\n")


def iter_fabric_nodes(data):
    """
    Yield each node mapping from any AVD node-type definition in fabric.yml.

    All AVD node types (pe, pe_full, pe_partial, p, rr, ...) share the shape:
        <node_type>:
          node_groups:
            - nodes:
                - name: FOO
          nodes:            # top-level, no group
            - name: BAR

    This generator yields node entries regardless of node-type key name or
    whether the node sits inside a node_group or directly under the node type.
    """
    # Known non-node-type top-level scalar/mapping keys to skip
    SKIP_KEYS = {
        "defaults", "node_groups", "nodes",
        "fabric_name", "dc_name", "mgmt_interface", "mgmt_interface_vrf",
        "mgmt_destination_networks", "mgmt_gateway",
        "underlay_routing_protocol", "underlay_ipv6",
        "isis_default_is_type", "isis_default_circuit_type",
        "isis_default_metric", "isis_ti_lfa",
        "overlay_routing_protocol", "evpn_overlay_bgp_rtc", "bgp_as",
        "overlay_rt_type", "overlay_rd_type", "bgp_peer_groups",
        "fabric_sflow", "sflow_settings", "custom_templates",
        "eos_designs_custom_templates", "core_interfaces",
    }

    for key, value in data.items():
        if key in SKIP_KEYS or not isinstance(value, dict):
            continue

        # Top-level nodes directly under the node-type key
        for node in value.get("nodes", []) or []:
            if isinstance(node, dict):
                yield node

        # Nodes nested inside node_groups
        for group in value.get("node_groups", []) or []:
            if not isinstance(group, dict):
                continue
            for node in group.get("nodes", []) or []:
                if isinstance(node, dict):
                    yield node


def patch_fabric_yml(
    node_peer_ips: dict[str, set[str]],
    fabric_yml: Path,
    dry_run: bool,
) -> None:
    """
    Locate each affected node anywhere in fabric.yml's node-type definitions
    and add raw_eos_cli with the dhcp relay sync neighbor block.
    Comments and formatting in the file are preserved via ruamel.yaml.
    """
    data = load_yaml(fabric_yml)
    modified = False

    for node_entry in iter_fabric_nodes(data):
        name = str(node_entry.get("name", ""))
        if name not in node_peer_ips:
            continue

        peer_ips = node_peer_ips[name]
        existing = str(node_entry.get("raw_eos_cli", "") or "")

        if "dhcp relay" in existing:
            print(f"  {name}: raw_eos_cli already has dhcp relay block — skipping.")
            continue

        cli = dhcp_relay_cli_block(peer_ips)
        node_entry["raw_eos_cli"] = (
            literal(existing.rstrip() + "\n!\n" + cli) if existing else cli
        )
        print(f"  {name}: sync neighbors → {sorted(peer_ips)}")
        modified = True

    if modified:
        save_yaml(fabric_yml, data, dry_run)
    else:
        print("  No changes needed in fabric.yml.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--inventory", default=str(INVENTORY_DEFAULT),
        help="AVD inventory directory (default: ./inventories)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print planned changes without writing files",
    )
    args = parser.parse_args()

    inv          = Path(args.inventory)
    gv           = inv / "group_vars"
    services_dir = gv / "services"
    fabric_yml   = gv / "mpls" / "fabric.yml"

    # 1. SVI profiles with PD relay
    svi_profiles = load_yaml(services_dir / "_svi_profiles.yml").get("svi_profiles", [])
    pd_profiles  = find_pd_profiles(svi_profiles)
    if not pd_profiles:
        print("No SVI profiles with DHCPv6 PD relay found. Nothing to do.")
        sys.exit(0)
    print(f"SVI profiles with DHCPv6 PD relay: {pd_profiles}")

    # 2. SVI → PE nodes
    svi_pe_map = svi_to_pe_nodes(
        services_dir,
        services_dir / "endpoints_pon_shelves.yml",
        pd_profiles,
    )
    if not svi_pe_map:
        print("No anycast-GW SVIs with DHCPv6 PD relay found. Nothing to do.")
        sys.exit(0)

    print("\nSVI → anycast-GW PE nodes:")
    for svi_id, nodes in sorted(svi_pe_map.items()):
        print(f"  SVI {svi_id}: {nodes}")

    # 3. P2P IP map from core_interfaces
    fabric   = load_yaml(fabric_yml)
    ci       = fabric.get("core_interfaces", {})
    node_p2p = build_p2p_ip_map(
        p2p_links = list(ci.get("p2p_links", [])),
        ip_pools  = list(ci.get("p2p_links_ip_pools", [])),
        profiles  = list(ci.get("p2p_links_profiles", [])),
    )

    print("\nResolved p2p IPs per node:")
    for node, ips in sorted(node_p2p.items()):
        print(f"  {node}: {ips}")

    # 4. For each node, collect peer IPs across all SVIs it participates in
    node_peer_ips: dict[str, set[str]] = {}
    for svi_id, nodes in sorted(svi_pe_map.items()):
        for node in nodes:
            peers = [n for n in nodes if n != node]
            for peer in peers:
                peer_ips = node_p2p.get(peer)
                if not peer_ips:
                    print(f"  Warning: no p2p IPs for {peer} (SVI {svi_id}) — skipping.")
                    continue
                node_peer_ips.setdefault(node, set()).add(peer_ips[0])

    if not node_peer_ips:
        print("\nNo peer IPs resolved. Verify fabric.yml and endpoints files.")
        sys.exit(1)

    # 5. Patch fabric.yml (preserving comments and formatting)
    print("\nPatching fabric.yml node entries:")
    patch_fabric_yml(node_peer_ips, fabric_yml, args.dry_run)

    print("\nDone. Run:\n  ansible-playbook playbooks/add_dhcpv6_pd_sync.yml --tags build")


if __name__ == "__main__":
    main()
