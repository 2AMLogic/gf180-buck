v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {gf180-buck :: power_stage -- HS pfet_06v0 (VIN-referenced, no bootstrap), LS nfet_06v0 (synchronous)
Sizing: Ron.W (tt, 27C, 5.0V gate drive, gf180-gate-driver 98ca4a8 spec 2.1): nfet 2.2246, pfet 7.1427 ohm.mm.
Whs=300x100u=30.00mm -> 238.1 mohm; Wls=224x100u=22.40mm -> 99.3 mohm; weighted at D=0.36: 149.3 mohm = 37.3 mW @500mA.
Unit instance W=100u (the model bin tops out at W=100.01u per instance), nf=10.
Derivation and caveats: design/README.md section power_stage. L: nfet 0.70u, pfet 0.55u (sibling test geometry).} -600 -700 0 0 0.35 0.35 {}
C {ipin.sym} -500 -300 0 0 {name=p1 lab=GH}
C {ipin.sym} -500 100 0 0 {name=p2 lab=GL}
C {iopin.sym} -500 -450 0 0 {name=p3 lab=VIN}
C {iopin.sym} 700 -100 0 0 {name=p4 lab=SW}
C {iopin.sym} -500 300 0 0 {name=p5 lab=GND}
C {pfet_06v0.sym} 0 -300 0 0 {name=MHS model=pfet_06v0 W=100u L=0.55u nf=10 m=300}
C {lab_pin.sym} -20 -300 0 0 {name=l6 lab=GH}
C {lab_pin.sym} 20 -300 0 0 {name=l7 lab=VIN}
C {lab_pin.sym} 20 -270 0 0 {name=l8 lab=SW}
C {lab_pin.sym} 20 -330 0 0 {name=l9 lab=VIN}
C {nfet_06v0.sym} 0 100 0 0 {name=MLS model=nfet_06v0 W=100u L=0.7u nf=10 m=224}
C {lab_pin.sym} -20 100 0 0 {name=l10 lab=GL}
C {lab_pin.sym} 20 100 0 0 {name=l11 lab=GND}
C {lab_pin.sym} 20 70 0 0 {name=l12 lab=SW}
C {lab_pin.sym} 20 130 0 0 {name=l13 lab=GND}
