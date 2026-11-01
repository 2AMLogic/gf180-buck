v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {compensator: type-III (Venable) network around the adopted error amplifier (R13, issue #35)} -600 -900 0 0 0.5 0.5 {}
T {Values are the design-to table of design/compensator.md (issue #17), not re-derived: Rtop 10k, Rbot 5k, R2 4.55k, R3 204,} -600 -850 0 0 0.3 0.3 {}
T {C1 1.75n, C2 35.7p, C3 780p; Vref 0.6 V, Vout 1.8 V.  Ideal R/C parts (design-to, not a BOM); C2 is small enough that layout} -600 -820 0 0 0.3 0.3 {}
T {parasitics will matter.  Zi = Rtop || (R3 + 1/sC3);  Zf = (R2 + 1/sC1) || 1/sC2.  VOUT is the converter output sense point.} -600 -790 0 0 0.3 0.3 {}
T {Error amplifier: gf180-opamp opamp_two_stage, adopted at interface (reuse.lock.json); drawn as a black-box symbol, nothing sized here.} -600 -760 0 0 0.3 0.3 {}
T {Its finite GBW into this load is NOT in the averaged model (compensator.md, Assumptions).} -600 -730 0 0 0.3 0.3 {}
C {ipin.sym} -900 -800 0 0 {name=p_VOUT lab=VOUT}
C {ipin.sym} -900 -760 0 0 {name=p_VREF lab=VREF}
C {ipin.sym} -900 -720 0 0 {name=p_IBIAS lab=IBIAS}
C {opin.sym} -900 -680 0 0 {name=p_VC lab=VC}
C {iopin.sym} -900 -640 0 0 {name=p_VDD33 lab=VDD33}
C {iopin.sym} -900 -600 0 0 {name=p_GND lab=GND}
C {res.sym} -400 -300 0 0 {name=Rtop value=10k footprint=1206 device=resistor m=1}
C {lab_pin.sym} -400 -330 0 0 {name=l_Rtop_P lab=VOUT}
C {lab_pin.sym} -400 -270 0 0 {name=l_Rtop_M lab=FBN}
C {res.sym} -100 -300 0 0 {name=R3 value=204 footprint=1206 device=resistor m=1}
C {lab_pin.sym} -100 -330 0 0 {name=l_R3_P lab=VOUT}
C {lab_pin.sym} -100 -270 0 0 {name=l_R3_M lab=X}
C {capa.sym} 200 -300 0 0 {name=C3 m=1 value=780p footprint=1206 device="ceramic capacitor"}
C {lab_pin.sym} 200 -330 0 0 {name=l_C3_P lab=X}
C {lab_pin.sym} 200 -270 0 0 {name=l_C3_M lab=FBN}
C {res.sym} 500 -300 0 0 {name=Rbot value=5k footprint=1206 device=resistor m=1}
C {lab_pin.sym} 500 -330 0 0 {name=l_Rbot_P lab=FBN}
C {lab_pin.sym} 500 -270 0 0 {name=l_Rbot_M lab=GND}
C {res.sym} 800 -300 0 0 {name=R2 value=4.55k footprint=1206 device=resistor m=1}
C {lab_pin.sym} 800 -330 0 0 {name=l_R2_P lab=FBN}
C {lab_pin.sym} 800 -270 0 0 {name=l_R2_M lab=Z}
C {capa.sym} 1100 -300 0 0 {name=C1 m=1 value=1.75n footprint=1206 device="ceramic capacitor"}
C {lab_pin.sym} 1100 -330 0 0 {name=l_C1_P lab=Z}
C {lab_pin.sym} 1100 -270 0 0 {name=l_C1_M lab=VC}
C {capa.sym} 1400 -300 0 0 {name=C2 m=1 value=35.7p footprint=1206 device="ceramic capacitor"}
C {lab_pin.sym} 1400 -330 0 0 {name=l_C2_P lab=FBN}
C {lab_pin.sym} 1400 -270 0 0 {name=l_C2_M lab=VC}
C {opamp_two_stage.sym} 200 700 0 0 {name=XEA}
C {lab_pin.sym} 120 600 0 0 {name=l_XEA_vdd lab=VDD33}
C {lab_pin.sym} 120 640 0 0 {name=l_XEA_vss lab=GND}
C {lab_pin.sym} 120 680 0 0 {name=l_XEA_vinp lab=VREF}
C {lab_pin.sym} 120 720 0 0 {name=l_XEA_vinn lab=FBN}
C {lab_pin.sym} 120 760 0 0 {name=l_XEA_ibias lab=IBIAS}
C {lab_pin.sym} 280 600 0 0 {name=l_XEA_vout lab=VC}
