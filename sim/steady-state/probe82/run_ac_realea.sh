#!/usr/bin/env bash
# Issue #82: loop gain of the averaged buck with real/ideal EA and a given modulator window.
# usage: run_ac_realea.sh <ea 0=real opamp|1=ideal 1e6|2=single-pole GBW> <ib_ea e.g. 10u> <vamp e.g. 0.613> [gbw e.g. 1.1meg]    (run from the repo root; single ngspice run)
set -euo pipefail
src=sim/steady-state/probe82/ac_realea.spice
mf=${GF180_MODEL_FILE:-$HOME/.volare/gf180mcuD/libs.tech/ngspice/sm141064.ngspice}
di=${GF180_DESIGN_INC:-$HOME/.volare/gf180mcuD/libs.tech/ngspice/design.ngspice}
tag="ie$1_ib$2_va$3_g${4:-na}"; deck=/tmp/ac82_$tag.cir; dat=/tmp/ac82_$tag.dat
case "$1" in 1) ea='s|^\*EA_IDEAL\* ||';; 2) ea='s|^\*EA_GBW\* ||';; *) ea='s|^\*EA_REAL\* ||';; esac
gbw=${4:-1.1meg}
{ sed -e "s|@MODEL_FILE@|$mf|" -e "s|@DESIGN_INC@|$di|" -e "$ea" "$src"
  printf '.param ib_ea=%s vamp=%s gbw=%s\n.control\nop\nprint v(vc) v(fbn) v(vo)\nac dec 100 1k 100meg\nlet T = -v(vo)/v(b)\nwrdata %s db(T) 180/pi*cph(T)\n.endc\n.end\n' "$2" "$3" "$gbw" "$dat"
} > "$deck"
timeout 100 ngspice -b -o "/tmp/ac82_$tag.log" "$deck" >/dev/null 2>&1 || true
grep -aE '^v\(' "/tmp/ac82_$tag.log" | tr '\n' ' '; echo
python3 -I - "$dat" "$tag" <<'PY'
import sys
rows=[list(map(float,l.split())) for l in open(sys.argv[1])]
f=[r[0] for r in rows]; g=[r[1] for r in rows]; p=[r[3] for r in rows]
up=[p[0]]
for x in p[1:]:
    while x-up[-1]>180: x-=360
    while x-up[-1]<-180: x+=360
    up.append(x)
out=[]
for i in range(len(f)-1):
    if g[i]>0>=g[i+1]: out.append("fc=%.1f kHz PM=%.1f deg"%(f[i]/1e3,180+up[i]))
    if up[i]>-180>=up[i+1]: out.append("phase=-180 at %.1f kHz (gain %.1f dB)"%(f[i]/1e3,g[i]))
print(sys.argv[2],"|"," ; ".join(out))
PY
