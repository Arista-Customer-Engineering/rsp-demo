# todo

## Backlog

- [ ] **CGNAT appliance NAT + HA**: Configure actual NAT translation on the
      100.64.x.x subscriber pools to public IPs on ALPHA-CG-NAT / BETA-CG-NAT,
      then set up HA state synchronization between the two units. The VPWS
      pseudowire for HA sync is already plumbed (`CGNAT_HA_FAILOVER` in
      `services_cg_nat.yml`); the NAT policy and HA state-sync config on the
      appliance nodes is what's missing.
