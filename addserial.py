#!/usr/bin/env python3
#
# Generates a "persistent" variant of the repo's containerlab topology for
# onboarding into a long-running local CloudVision instance: a deterministic
# per-node serial number (so CVP re-recognizes the same lab across restarts)
# and the CVP onboarding token, bound into every AVD-built fabric node.
#
# The base *.clab.yml is never modified - this reads it and writes a sibling
# <name>.persistent.clab.yml. Simulation-only nodes (TRANSIT, CG-NAT
# appliances, PON shelves - anything without a startup-config, i.e. not
# built by eos_designs) are left without a CVP onboarding token, since
# they're not real network elements to manage in CVP.

import os
import sys

from ruamel.yaml import YAML

yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)

base_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()

topofile = None
with os.scandir(base_dir) as entries:
    for entry in entries:
        if entry.name.endswith(('.clab.yml', '.clab.yaml')) and '.persistent.' not in entry.name:
            topofile = entry.path
            break

if topofile is None:
    sys.exit(f'no *.clab.yml topology found in {base_dir}')

with open(topofile) as f:
    clab_topo = yaml.load(f)

serial_dir = os.path.join(base_dir, 'clab_eos_serial')
cv_token_path = os.path.join(base_dir, 'cv-token', 'cv-onboarding-token')

for name, node in clab_topo['topology']['nodes'].items():
    kind = node.get('kind')

    if kind in ('ceos', 'arista_ceos'):
        node_serial_dir = os.path.join(serial_dir, name)
        os.makedirs(node_serial_dir, exist_ok=True)
        with open(os.path.join(node_serial_dir, 'ceos-config'), 'w') as f:
            f.write(f'SERIALNUMBER={str(abs(hash(name)))[:11]}')

        copy_to_flash = [f'./clab_eos_serial/{name}/ceos-config']
        if 'startup-config' in node and os.path.exists(cv_token_path):
            copy_to_flash.append('./cv-token/cv-onboarding-token')
        node['extras'] = {'ceos-copy-to-flash': copy_to_flash}

    elif kind in ('veos', 'arista_veos'):
        node_serial_dir = os.path.join(serial_dir, name)
        os.makedirs(node_serial_dir, exist_ok=True)
        with open(os.path.join(node_serial_dir, 'veos-config'), 'w') as f:
            f.write(f'SERIALNUMBER={str(abs(hash(name)))[:11]}')
        node['binds'] = node.get('binds', []) + [f'./clab_eos_serial/{name}/veos-config:/mnt/flash/veos-config']

base, ext = topofile.rsplit('.clab.', 1)
outfile = f'{base}.persistent.clab.{ext}'
with open(outfile, 'w') as f:
    yaml.dump(clab_topo, f)

print(f'wrote {outfile}')
