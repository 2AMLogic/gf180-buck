v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {gf180-buck :: gate_drive -- 3.3V PWM -> VIN-domain level shift -> dead-time (sensed non-overlap + delay) -> tapered GH/GL drivers.
VDD3 domain: 03v3 devices. VIN domain: 06v0 devices only. No VIN-domain node ever returns to a 03v3 gate (see design/README.md, 8.8).
Dead time = (sense inverter + delay + NAND/NOR + 6-stage driver) - (gate fall to Vth). Gate drivers run from VIN, not the 3.3V rail (record 0003 2.3).} -800 -1700 0 0 0.35 0.35 {}
C {ipin.sym} -800 -1300 0 0 {name=p1 lab=PWM}
C {iopin.sym} -800 -1250 0 0 {name=p2 lab=VDD3}
C {iopin.sym} -800 -1200 0 0 {name=p3 lab=VIN}
C {iopin.sym} -800 -1150 0 0 {name=p4 lab=GND}
C {opin.sym} 2000 -1300 0 0 {name=p5 lab=GH}
C {opin.sym} 2000 -1200 0 0 {name=p6 lab=GL}
C {pfet_03v3.sym} -600 -1080 0 0 {name=MP_I0 model=pfet_03v3 W=2.5u L=0.28u nf=1 m=1}
C {lab_pin.sym} -620 -1080 0 0 {name=l7 lab=PWM}
C {lab_pin.sym} -580 -1080 0 0 {name=l8 lab=VDD3}
C {lab_pin.sym} -580 -1050 0 0 {name=l9 lab=PWMB}
C {lab_pin.sym} -580 -1110 0 0 {name=l10 lab=VDD3}
C {nfet_03v3.sym} -600 -920 0 0 {name=MN_I0 model=nfet_03v3 W=1u L=0.28u nf=1 m=1}
C {lab_pin.sym} -620 -920 0 0 {name=l11 lab=PWM}
C {lab_pin.sym} -580 -920 0 0 {name=l12 lab=GND}
C {lab_pin.sym} -580 -950 0 0 {name=l13 lab=PWMB}
C {lab_pin.sym} -580 -890 0 0 {name=l14 lab=GND}
C {pfet_03v3.sym} -300 -1080 0 0 {name=MP_I1 model=pfet_03v3 W=2.5u L=0.28u nf=1 m=1}
C {lab_pin.sym} -320 -1080 0 0 {name=l15 lab=PWMB}
C {lab_pin.sym} -280 -1080 0 0 {name=l16 lab=VDD3}
C {lab_pin.sym} -280 -1050 0 0 {name=l17 lab=PWMT}
C {lab_pin.sym} -280 -1110 0 0 {name=l18 lab=VDD3}
C {nfet_03v3.sym} -300 -920 0 0 {name=MN_I1 model=nfet_03v3 W=1u L=0.28u nf=1 m=1}
C {lab_pin.sym} -320 -920 0 0 {name=l19 lab=PWMB}
C {lab_pin.sym} -280 -920 0 0 {name=l20 lab=GND}
C {lab_pin.sym} -280 -950 0 0 {name=l21 lab=PWMT}
C {lab_pin.sym} -280 -890 0 0 {name=l22 lab=GND}
C {nfet_06v0.sym} 100 -920 0 0 {name=MN_LS1 model=nfet_06v0 W=20u L=0.7u nf=2 m=1}
C {lab_pin.sym} 80 -920 0 0 {name=l23 lab=PWMT}
C {lab_pin.sym} 120 -920 0 0 {name=l24 lab=GND}
C {lab_pin.sym} 120 -950 0 0 {name=l25 lab=QB}
C {lab_pin.sym} 120 -890 0 0 {name=l26 lab=GND}
C {nfet_06v0.sym} 500 -920 0 0 {name=MN_LS2 model=nfet_06v0 W=20u L=0.7u nf=2 m=1}
C {lab_pin.sym} 480 -920 0 0 {name=l27 lab=PWMB}
C {lab_pin.sym} 520 -920 0 0 {name=l28 lab=GND}
C {lab_pin.sym} 520 -950 0 0 {name=l29 lab=Q}
C {lab_pin.sym} 520 -890 0 0 {name=l30 lab=GND}
C {pfet_06v0.sym} 100 -1080 0 0 {name=MP_LS1 model=pfet_06v0 W=3u L=0.55u nf=1 m=1}
C {lab_pin.sym} 80 -1080 0 0 {name=l31 lab=Q}
C {lab_pin.sym} 120 -1080 0 0 {name=l32 lab=VIN}
C {lab_pin.sym} 120 -1050 0 0 {name=l33 lab=QB}
C {lab_pin.sym} 120 -1110 0 0 {name=l34 lab=VIN}
C {pfet_06v0.sym} 500 -1080 0 0 {name=MP_LS2 model=pfet_06v0 W=3u L=0.55u nf=1 m=1}
C {lab_pin.sym} 480 -1080 0 0 {name=l35 lab=QB}
C {lab_pin.sym} 520 -1080 0 0 {name=l36 lab=VIN}
C {lab_pin.sym} 520 -1050 0 0 {name=l37 lab=Q}
C {lab_pin.sym} 520 -1110 0 0 {name=l38 lab=VIN}
C {pfet_06v0.sym} 1000 -1080 0 0 {name=MP_Q1 model=pfet_06v0 W=9u L=0.55u nf=1 m=1}
C {lab_pin.sym} 980 -1080 0 0 {name=l39 lab=Q}
C {lab_pin.sym} 1020 -1080 0 0 {name=l40 lab=VIN}
C {lab_pin.sym} 1020 -1050 0 0 {name=l41 lab=QI}
C {lab_pin.sym} 1020 -1110 0 0 {name=l42 lab=VIN}
C {nfet_06v0.sym} 1000 -920 0 0 {name=MN_Q1 model=nfet_06v0 W=3u L=0.7u nf=1 m=1}
C {lab_pin.sym} 980 -920 0 0 {name=l43 lab=Q}
C {lab_pin.sym} 1020 -920 0 0 {name=l44 lab=GND}
C {lab_pin.sym} 1020 -950 0 0 {name=l45 lab=QI}
C {lab_pin.sym} 1020 -890 0 0 {name=l46 lab=GND}
C {pfet_06v0.sym} 1300 -1080 0 0 {name=MP_Q2 model=pfet_06v0 W=18u L=0.55u nf=2 m=1}
C {lab_pin.sym} 1280 -1080 0 0 {name=l47 lab=QI}
C {lab_pin.sym} 1320 -1080 0 0 {name=l48 lab=VIN}
C {lab_pin.sym} 1320 -1050 0 0 {name=l49 lab=A}
C {lab_pin.sym} 1320 -1110 0 0 {name=l50 lab=VIN}
C {nfet_06v0.sym} 1300 -920 0 0 {name=MN_Q2 model=nfet_06v0 W=6u L=0.7u nf=1 m=1}
C {lab_pin.sym} 1280 -920 0 0 {name=l51 lab=QI}
C {lab_pin.sym} 1320 -920 0 0 {name=l52 lab=GND}
C {lab_pin.sym} 1320 -950 0 0 {name=l53 lab=A}
C {lab_pin.sym} 1320 -890 0 0 {name=l54 lab=GND}
C {pfet_06v0.sym} -600 -680 0 0 {name=MP_HDa model=pfet_06v0 W=9u L=0.55u nf=1 m=1}
C {lab_pin.sym} -620 -680 0 0 {name=l55 lab=A}
C {lab_pin.sym} -580 -680 0 0 {name=l56 lab=VIN}
C {lab_pin.sym} -580 -650 0 0 {name=l57 lab=HD0}
C {lab_pin.sym} -580 -710 0 0 {name=l58 lab=VIN}
C {pfet_06v0.sym} -350 -680 0 0 {name=MP_HDb model=pfet_06v0 W=9u L=0.55u nf=1 m=1}
C {lab_pin.sym} -370 -680 0 0 {name=l59 lab=LSOFFD}
C {lab_pin.sym} -330 -680 0 0 {name=l60 lab=VIN}
C {lab_pin.sym} -330 -650 0 0 {name=l61 lab=HD0}
C {lab_pin.sym} -330 -710 0 0 {name=l62 lab=VIN}
C {nfet_06v0.sym} -600 -520 0 0 {name=MN_HDa model=nfet_06v0 W=8u L=0.7u nf=1 m=1}
C {lab_pin.sym} -620 -520 0 0 {name=l63 lab=A}
C {lab_pin.sym} -580 -520 0 0 {name=l64 lab=GND}
C {lab_pin.sym} -580 -550 0 0 {name=l65 lab=HD0}
C {lab_pin.sym} -580 -490 0 0 {name=l66 lab=HD_x}
C {nfet_06v0.sym} -350 -520 0 0 {name=MN_HDb model=nfet_06v0 W=8u L=0.7u nf=1 m=1}
C {lab_pin.sym} -370 -520 0 0 {name=l67 lab=LSOFFD}
C {lab_pin.sym} -330 -520 0 0 {name=l68 lab=GND}
C {lab_pin.sym} -330 -550 0 0 {name=l69 lab=HD_x}
C {lab_pin.sym} -330 -490 0 0 {name=l70 lab=GND}
C {pfet_06v0.sym} 100 -680 0 0 {name=MP_LDa model=pfet_06v0 W=22u L=0.55u nf=3 m=1}
C {lab_pin.sym} 80 -680 0 0 {name=l71 lab=A}
C {lab_pin.sym} 120 -680 0 0 {name=l72 lab=VIN}
C {lab_pin.sym} 120 -650 0 0 {name=l73 lab=LD_x}
C {lab_pin.sym} 120 -710 0 0 {name=l74 lab=VIN}
C {pfet_06v0.sym} 350 -680 0 0 {name=MP_LDb model=pfet_06v0 W=22u L=0.55u nf=3 m=1}
C {lab_pin.sym} 330 -680 0 0 {name=l75 lab=HSOND}
C {lab_pin.sym} 370 -680 0 0 {name=l76 lab=VIN}
C {lab_pin.sym} 370 -650 0 0 {name=l77 lab=LD0}
C {lab_pin.sym} 370 -710 0 0 {name=l78 lab=LD_x}
C {nfet_06v0.sym} 100 -520 0 0 {name=MN_LDa model=nfet_06v0 W=4u L=0.7u nf=1 m=1}
C {lab_pin.sym} 80 -520 0 0 {name=l79 lab=A}
C {lab_pin.sym} 120 -520 0 0 {name=l80 lab=GND}
C {lab_pin.sym} 120 -550 0 0 {name=l81 lab=LD0}
C {lab_pin.sym} 120 -490 0 0 {name=l82 lab=GND}
C {nfet_06v0.sym} 350 -520 0 0 {name=MN_LDb model=nfet_06v0 W=4u L=0.7u nf=1 m=1}
C {lab_pin.sym} 330 -520 0 0 {name=l83 lab=HSOND}
C {lab_pin.sym} 370 -520 0 0 {name=l84 lab=GND}
C {lab_pin.sym} 370 -550 0 0 {name=l85 lab=LD0}
C {lab_pin.sym} 370 -490 0 0 {name=l86 lab=GND}
C {pfet_06v0.sym} 900 -680 0 0 {name=MP_SL model=pfet_06v0 W=4u L=0.55u nf=1 m=1}
C {lab_pin.sym} 880 -680 0 0 {name=l87 lab=GL}
C {lab_pin.sym} 920 -680 0 0 {name=l88 lab=VIN}
C {lab_pin.sym} 920 -650 0 0 {name=l89 lab=LSOFF}
C {lab_pin.sym} 920 -710 0 0 {name=l90 lab=VIN}
C {nfet_06v0.sym} 900 -520 0 0 {name=MN_SL model=nfet_06v0 W=20u L=0.7u nf=2 m=1}
C {lab_pin.sym} 880 -520 0 0 {name=l91 lab=GL}
C {lab_pin.sym} 920 -520 0 0 {name=l92 lab=GND}
C {lab_pin.sym} 920 -550 0 0 {name=l93 lab=LSOFF}
C {lab_pin.sym} 920 -490 0 0 {name=l94 lab=GND}
C {pfet_06v0.sym} 1200 -680 0 0 {name=MP_SH model=pfet_06v0 W=20u L=0.55u nf=2 m=1}
C {lab_pin.sym} 1180 -680 0 0 {name=l95 lab=GH}
C {lab_pin.sym} 1220 -680 0 0 {name=l96 lab=VIN}
C {lab_pin.sym} 1220 -650 0 0 {name=l97 lab=HSON}
C {lab_pin.sym} 1220 -710 0 0 {name=l98 lab=VIN}
C {nfet_06v0.sym} 1200 -520 0 0 {name=MN_SH model=nfet_06v0 W=3u L=0.7u nf=1 m=1}
C {lab_pin.sym} 1180 -520 0 0 {name=l99 lab=GH}
C {lab_pin.sym} 1220 -520 0 0 {name=l100 lab=GND}
C {lab_pin.sym} 1220 -550 0 0 {name=l101 lab=HSON}
C {lab_pin.sym} 1220 -490 0 0 {name=l102 lab=GND}
C {pfet_06v0.sym} 1500 -680 0 0 {name=MP_DL0 model=pfet_06v0 W=6u L=3.5u nf=1 m=1}
C {lab_pin.sym} 1480 -680 0 0 {name=l103 lab=LSOFF}
C {lab_pin.sym} 1520 -680 0 0 {name=l104 lab=VIN}
C {lab_pin.sym} 1520 -650 0 0 {name=l105 lab=LDL0}
C {lab_pin.sym} 1520 -710 0 0 {name=l106 lab=VIN}
C {nfet_06v0.sym} 1500 -520 0 0 {name=MN_DL0 model=nfet_06v0 W=2u L=3.5u nf=1 m=1}
C {lab_pin.sym} 1480 -520 0 0 {name=l107 lab=LSOFF}
C {lab_pin.sym} 1520 -520 0 0 {name=l108 lab=GND}
C {lab_pin.sym} 1520 -550 0 0 {name=l109 lab=LDL0}
C {lab_pin.sym} 1520 -490 0 0 {name=l110 lab=GND}
C {pfet_06v0.sym} 1500 -280 0 0 {name=MP_DH0 model=pfet_06v0 W=6u L=3.5u nf=1 m=1}
C {lab_pin.sym} 1480 -280 0 0 {name=l111 lab=HSON}
C {lab_pin.sym} 1520 -280 0 0 {name=l112 lab=VIN}
C {lab_pin.sym} 1520 -250 0 0 {name=l113 lab=HDL0}
C {lab_pin.sym} 1520 -310 0 0 {name=l114 lab=VIN}
C {nfet_06v0.sym} 1500 -120 0 0 {name=MN_DH0 model=nfet_06v0 W=2u L=3.5u nf=1 m=1}
C {lab_pin.sym} 1480 -120 0 0 {name=l115 lab=HSON}
C {lab_pin.sym} 1520 -120 0 0 {name=l116 lab=GND}
C {lab_pin.sym} 1520 -150 0 0 {name=l117 lab=HDL0}
C {lab_pin.sym} 1520 -90 0 0 {name=l118 lab=GND}
C {pfet_06v0.sym} 1800 -680 0 0 {name=MP_DL1 model=pfet_06v0 W=6u L=3.5u nf=1 m=1}
C {lab_pin.sym} 1780 -680 0 0 {name=l119 lab=LDL0}
C {lab_pin.sym} 1820 -680 0 0 {name=l120 lab=VIN}
C {lab_pin.sym} 1820 -650 0 0 {name=l121 lab=LSOFFD}
C {lab_pin.sym} 1820 -710 0 0 {name=l122 lab=VIN}
C {nfet_06v0.sym} 1800 -520 0 0 {name=MN_DL1 model=nfet_06v0 W=2u L=3.5u nf=1 m=1}
C {lab_pin.sym} 1780 -520 0 0 {name=l123 lab=LDL0}
C {lab_pin.sym} 1820 -520 0 0 {name=l124 lab=GND}
C {lab_pin.sym} 1820 -550 0 0 {name=l125 lab=LSOFFD}
C {lab_pin.sym} 1820 -490 0 0 {name=l126 lab=GND}
C {pfet_06v0.sym} 1800 -280 0 0 {name=MP_DH1 model=pfet_06v0 W=6u L=3.5u nf=1 m=1}
C {lab_pin.sym} 1780 -280 0 0 {name=l127 lab=HDL0}
C {lab_pin.sym} 1820 -280 0 0 {name=l128 lab=VIN}
C {lab_pin.sym} 1820 -250 0 0 {name=l129 lab=HSOND}
C {lab_pin.sym} 1820 -310 0 0 {name=l130 lab=VIN}
C {nfet_06v0.sym} 1800 -120 0 0 {name=MN_DH1 model=nfet_06v0 W=2u L=3.5u nf=1 m=1}
C {lab_pin.sym} 1780 -120 0 0 {name=l131 lab=HDL0}
C {lab_pin.sym} 1820 -120 0 0 {name=l132 lab=GND}
C {lab_pin.sym} 1820 -150 0 0 {name=l133 lab=HSOND}
C {lab_pin.sym} 1820 -90 0 0 {name=l134 lab=GND}
C {pfet_06v0.sym} -600 -180 0 0 {name=MP_HG0 model=pfet_06v0 W=9u L=0.55u nf=1 m=1}
C {lab_pin.sym} -620 -180 0 0 {name=l135 lab=HD0}
C {lab_pin.sym} -580 -180 0 0 {name=l136 lab=VIN}
C {lab_pin.sym} -580 -150 0 0 {name=l137 lab=hg0}
C {lab_pin.sym} -580 -210 0 0 {name=l138 lab=VIN}
C {nfet_06v0.sym} -600 -20 0 0 {name=MN_HG0 model=nfet_06v0 W=3u L=0.7u nf=1 m=1}
C {lab_pin.sym} -620 -20 0 0 {name=l139 lab=HD0}
C {lab_pin.sym} -580 -20 0 0 {name=l140 lab=GND}
C {lab_pin.sym} -580 -50 0 0 {name=l141 lab=hg0}
C {lab_pin.sym} -580 10 0 0 {name=l142 lab=GND}
C {pfet_06v0.sym} -300 -180 0 0 {name=MP_HG1 model=pfet_06v0 W=30u L=0.55u nf=3 m=1}
C {lab_pin.sym} -320 -180 0 0 {name=l143 lab=hg0}
C {lab_pin.sym} -280 -180 0 0 {name=l144 lab=VIN}
C {lab_pin.sym} -280 -150 0 0 {name=l145 lab=hg1}
C {lab_pin.sym} -280 -210 0 0 {name=l146 lab=VIN}
C {nfet_06v0.sym} -300 -20 0 0 {name=MN_HG1 model=nfet_06v0 W=10u L=0.7u nf=1 m=1}
C {lab_pin.sym} -320 -20 0 0 {name=l147 lab=hg0}
C {lab_pin.sym} -280 -20 0 0 {name=l148 lab=GND}
C {lab_pin.sym} -280 -50 0 0 {name=l149 lab=hg1}
C {lab_pin.sym} -280 10 0 0 {name=l150 lab=GND}
C {pfet_06v0.sym} 2 -180 0 0 {name=MP_HG2 model=pfet_06v0 W=51u L=0.55u nf=11 m=2}
C {lab_pin.sym} -18 -180 0 0 {name=l151 lab=hg1}
C {lab_pin.sym} 22 -180 0 0 {name=l152 lab=VIN}
C {lab_pin.sym} 22 -150 0 0 {name=l153 lab=hg2}
C {lab_pin.sym} 22 -210 0 0 {name=l154 lab=VIN}
C {nfet_06v0.sym} 2 -20 0 0 {name=MN_HG2 model=nfet_06v0 W=34u L=0.7u nf=4 m=1}
C {lab_pin.sym} -18 -20 0 0 {name=l155 lab=hg1}
C {lab_pin.sym} 22 -20 0 0 {name=l156 lab=GND}
C {lab_pin.sym} 22 -50 0 0 {name=l157 lab=hg2}
C {lab_pin.sym} 22 10 0 0 {name=l158 lab=GND}
C {pfet_06v0.sym} 310 -180 0 0 {name=MP_HG3 model=pfet_06v0 W=69u L=0.55u nf=35 m=5}
C {lab_pin.sym} 290 -180 0 0 {name=l159 lab=hg2}
C {lab_pin.sym} 330 -180 0 0 {name=l160 lab=VIN}
C {lab_pin.sym} 330 -150 0 0 {name=l161 lab=hg3}
C {lab_pin.sym} 330 -210 0 0 {name=l162 lab=VIN}
C {nfet_06v0.sym} 310 -20 0 0 {name=MN_HG3 model=nfet_06v0 W=57.5u L=0.7u nf=12 m=2}
C {lab_pin.sym} 290 -20 0 0 {name=l163 lab=hg2}
C {lab_pin.sym} 330 -20 0 0 {name=l164 lab=GND}
C {lab_pin.sym} 330 -50 0 0 {name=l165 lab=hg3}
C {lab_pin.sym} 330 10 0 0 {name=l166 lab=GND}
C {pfet_06v0.sym} 638 -180 0 0 {name=MP_HG4 model=pfet_06v0 W=78u L=0.55u nf=117 m=15}
C {lab_pin.sym} 618 -180 0 0 {name=l167 lab=hg3}
C {lab_pin.sym} 658 -180 0 0 {name=l168 lab=VIN}
C {lab_pin.sym} 658 -150 0 0 {name=l169 lab=hg4}
C {lab_pin.sym} 658 -210 0 0 {name=l170 lab=VIN}
C {nfet_06v0.sym} 638 -20 0 0 {name=MN_HG4 model=nfet_06v0 W=78u L=0.7u nf=39 m=5}
C {lab_pin.sym} 618 -20 0 0 {name=l171 lab=hg3}
C {lab_pin.sym} 658 -20 0 0 {name=l172 lab=GND}
C {lab_pin.sym} 658 -50 0 0 {name=l173 lab=hg4}
C {lab_pin.sym} 658 10 0 0 {name=l174 lab=GND}
C {pfet_06v0.sym} 1035 -180 0 0 {name=MP_HG5 model=pfet_06v0 W=79.245u L=0.55u nf=420 m=53}
C {lab_pin.sym} 1015 -180 0 0 {name=l175 lab=hg4}
C {lab_pin.sym} 1055 -180 0 0 {name=l176 lab=VIN}
C {lab_pin.sym} 1055 -150 0 0 {name=l177 lab=GH}
C {lab_pin.sym} 1055 -210 0 0 {name=l178 lab=VIN}
C {nfet_06v0.sym} 1035 -20 0 0 {name=MN_HG5 model=nfet_06v0 W=77.778u L=0.7u nf=140 m=18}
C {lab_pin.sym} 1015 -20 0 0 {name=l179 lab=hg4}
C {lab_pin.sym} 1055 -20 0 0 {name=l180 lab=GND}
C {lab_pin.sym} 1055 -50 0 0 {name=l181 lab=GH}
C {lab_pin.sym} 1055 10 0 0 {name=l182 lab=GND}
C {pfet_06v0.sym} -600 220 0 0 {name=MP_LG0 model=pfet_06v0 W=9u L=0.55u nf=1 m=1}
C {lab_pin.sym} -620 220 0 0 {name=l183 lab=LD0}
C {lab_pin.sym} -580 220 0 0 {name=l184 lab=VIN}
C {lab_pin.sym} -580 250 0 0 {name=l185 lab=lg0}
C {lab_pin.sym} -580 190 0 0 {name=l186 lab=VIN}
C {nfet_06v0.sym} -600 380 0 0 {name=MN_LG0 model=nfet_06v0 W=3u L=0.7u nf=1 m=1}
C {lab_pin.sym} -620 380 0 0 {name=l187 lab=LD0}
C {lab_pin.sym} -580 380 0 0 {name=l188 lab=GND}
C {lab_pin.sym} -580 350 0 0 {name=l189 lab=lg0}
C {lab_pin.sym} -580 410 0 0 {name=l190 lab=GND}
C {pfet_06v0.sym} -300 220 0 0 {name=MP_LG1 model=pfet_06v0 W=30u L=0.55u nf=3 m=1}
C {lab_pin.sym} -320 220 0 0 {name=l191 lab=lg0}
C {lab_pin.sym} -280 220 0 0 {name=l192 lab=VIN}
C {lab_pin.sym} -280 250 0 0 {name=l193 lab=lg1}
C {lab_pin.sym} -280 190 0 0 {name=l194 lab=VIN}
C {nfet_06v0.sym} -300 380 0 0 {name=MN_LG1 model=nfet_06v0 W=10u L=0.7u nf=1 m=1}
C {lab_pin.sym} -320 380 0 0 {name=l195 lab=lg0}
C {lab_pin.sym} -280 380 0 0 {name=l196 lab=GND}
C {lab_pin.sym} -280 350 0 0 {name=l197 lab=lg1}
C {lab_pin.sym} -280 410 0 0 {name=l198 lab=GND}
C {pfet_06v0.sym} 2 220 0 0 {name=MP_LG2 model=pfet_06v0 W=51u L=0.55u nf=11 m=2}
C {lab_pin.sym} -18 220 0 0 {name=l199 lab=lg1}
C {lab_pin.sym} 22 220 0 0 {name=l200 lab=VIN}
C {lab_pin.sym} 22 250 0 0 {name=l201 lab=lg2}
C {lab_pin.sym} 22 190 0 0 {name=l202 lab=VIN}
C {nfet_06v0.sym} 2 380 0 0 {name=MN_LG2 model=nfet_06v0 W=34u L=0.7u nf=4 m=1}
C {lab_pin.sym} -18 380 0 0 {name=l203 lab=lg1}
C {lab_pin.sym} 22 380 0 0 {name=l204 lab=GND}
C {lab_pin.sym} 22 350 0 0 {name=l205 lab=lg2}
C {lab_pin.sym} 22 410 0 0 {name=l206 lab=GND}
C {pfet_06v0.sym} 310 220 0 0 {name=MP_LG3 model=pfet_06v0 W=69u L=0.55u nf=35 m=5}
C {lab_pin.sym} 290 220 0 0 {name=l207 lab=lg2}
C {lab_pin.sym} 330 220 0 0 {name=l208 lab=VIN}
C {lab_pin.sym} 330 250 0 0 {name=l209 lab=lg3}
C {lab_pin.sym} 330 190 0 0 {name=l210 lab=VIN}
C {nfet_06v0.sym} 310 380 0 0 {name=MN_LG3 model=nfet_06v0 W=57.5u L=0.7u nf=12 m=2}
C {lab_pin.sym} 290 380 0 0 {name=l211 lab=lg2}
C {lab_pin.sym} 330 380 0 0 {name=l212 lab=GND}
C {lab_pin.sym} 330 350 0 0 {name=l213 lab=lg3}
C {lab_pin.sym} 330 410 0 0 {name=l214 lab=GND}
C {pfet_06v0.sym} 638 220 0 0 {name=MP_LG4 model=pfet_06v0 W=78u L=0.55u nf=117 m=15}
C {lab_pin.sym} 618 220 0 0 {name=l215 lab=lg3}
C {lab_pin.sym} 658 220 0 0 {name=l216 lab=VIN}
C {lab_pin.sym} 658 250 0 0 {name=l217 lab=lg4}
C {lab_pin.sym} 658 190 0 0 {name=l218 lab=VIN}
C {nfet_06v0.sym} 638 380 0 0 {name=MN_LG4 model=nfet_06v0 W=78u L=0.7u nf=39 m=5}
C {lab_pin.sym} 618 380 0 0 {name=l219 lab=lg3}
C {lab_pin.sym} 658 380 0 0 {name=l220 lab=GND}
C {lab_pin.sym} 658 350 0 0 {name=l221 lab=lg4}
C {lab_pin.sym} 658 410 0 0 {name=l222 lab=GND}
C {pfet_06v0.sym} 1035 220 0 0 {name=MP_LG5 model=pfet_06v0 W=79.245u L=0.55u nf=420 m=53}
C {lab_pin.sym} 1015 220 0 0 {name=l223 lab=lg4}
C {lab_pin.sym} 1055 220 0 0 {name=l224 lab=VIN}
C {lab_pin.sym} 1055 250 0 0 {name=l225 lab=GL}
C {lab_pin.sym} 1055 190 0 0 {name=l226 lab=VIN}
C {nfet_06v0.sym} 1035 380 0 0 {name=MN_LG5 model=nfet_06v0 W=77.778u L=0.7u nf=140 m=18}
C {lab_pin.sym} 1015 380 0 0 {name=l227 lab=lg4}
C {lab_pin.sym} 1055 380 0 0 {name=l228 lab=GND}
C {lab_pin.sym} 1055 350 0 0 {name=l229 lab=GL}
C {lab_pin.sym} 1055 410 0 0 {name=l230 lab=GND}
