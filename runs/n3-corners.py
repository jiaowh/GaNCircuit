import os, subprocess, sys
X = 'vendor/epc/epc90133/reconstruction/export'
ext = [f'stock={X}/stock/extraction/G-m1-mid-stock.json', 'N3_00=results/gan/network-search/networks/N3_00.json',
       'N3_04=results/gan/network-search/networks/N3_04.json']
only = [f"{n}@{a}-Ls50-gear-l{f}" for n in ('stock', 'N3_00', 'N3_04') for a in ('ramp', 'step') for f in ('0.9', '1.1')]
cmd = [sys.executable, 'scripts/epc90133_switching.py', '--study', 'goals', '--jobs', '4', '--timeout', '3600',
       '--ext-file', *ext, '--only', *only, '--output', 'results/gan/network-search/round3c-corners.json']
with open('runs/network-search-round3c.log', 'w') as log:
    sys.exit(subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=dict(os.environ, PYTHONPATH='src')).returncode)
