v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {soft_start: analog reference ramp, no counter (R15)} -600 -900 0 0 0.5 0.5 {}
T {Iss (IBIAS mirrored down ~1:80, nom. ~125 nA) charges CSS; EN low holds CSS at 0.  VREF_SS = min(CSS, VBG) from a} -600 -850 0 0 0.3 0.3 {}
T {PMOS-input unity-gain OTA with CSS and VBG as parallel inputs (the lower gate wins, PMOS conducts more).} -600 -820 0 0 0.3 0.3 {}
T {VREF_SS feeds the error-amplifier reference input; VBG is the adopted bandgap's 1.20 V output.} -600 -790 0 0 0.3 0.3 {}
T {Ramp time 0 -> 1.2 V = CSS*1.2/Iss; the R15 window is 100-500 us (target tier).} -600 -760 0 0 0.3 0.3 {}
C {ipin.sym} -900 -800 0 0 {name=p_IBIAS lab=IBIAS}
C {ipin.sym} -900 -760 0 0 {name=p_VBG lab=VBG}
C {ipin.sym} -900 -720 0 0 {name=p_EN lab=EN}
C {opin.sym} -900 -680 0 0 {name=p_VREF_SS lab=VREF_SS}
C {opin.sym} -900 -640 0 0 {name=p_CSS lab=CSS}
C {iopin.sym} -900 -600 0 0 {name=p_VDD33 lab=VDD33}
C {iopin.sym} -900 -560 0 0 {name=p_VSS lab=VSS}
C {nfet_03v3.sym} -400 -300 0 0 {name=MN0 model=nfet_03v3 W=10u L=2u nf=1 m=1}
C {lab_pin.sym} -380 -330 0 0 {name=l_MN0_D lab=IBIAS}
C {lab_pin.sym} -420 -300 0 0 {name=l_MN0_G lab=IBIAS}
C {lab_pin.sym} -380 -270 0 0 {name=l_MN0_S lab=VSS}
C {lab_pin.sym} -380 -300 0 0 {name=l_MN0_B lab=VSS}
C {nfet_03v3.sym} -100 -300 0 0 {name=MNS model=nfet_03v3 W=1u L=16u nf=1 m=1}
C {lab_pin.sym} -80 -330 0 0 {name=l_MNS_D lab=SD}
C {lab_pin.sym} -120 -300 0 0 {name=l_MNS_G lab=IBIAS}
C {lab_pin.sym} -80 -270 0 0 {name=l_MNS_S lab=VSS}
C {lab_pin.sym} -80 -300 0 0 {name=l_MNS_B lab=VSS}
C {pfet_03v3.sym} 200 -300 0 0 {name=MP0 model=pfet_03v3 W=4u L=4u nf=1 m=1}
C {lab_pin.sym} 220 -270 0 0 {name=l_MP0_D lab=SD}
C {lab_pin.sym} 180 -300 0 0 {name=l_MP0_G lab=SD}
C {lab_pin.sym} 220 -330 0 0 {name=l_MP0_S lab=VDD33}
C {lab_pin.sym} 220 -300 0 0 {name=l_MP0_B lab=VDD33}
C {pfet_03v3.sym} 500 -300 0 0 {name=MP1 model=pfet_03v3 W=4u L=4u nf=1 m=1}
C {lab_pin.sym} 520 -270 0 0 {name=l_MP1_D lab=CSS}
C {lab_pin.sym} 480 -300 0 0 {name=l_MP1_G lab=SD}
C {lab_pin.sym} 520 -330 0 0 {name=l_MP1_S lab=VDD33}
C {lab_pin.sym} 520 -300 0 0 {name=l_MP1_B lab=VDD33}
C {cap_mim_2f0fF.sym} 800 -300 0 0 {name=CS model=cap_mim_2f0fF W=100u L=100u m=1}
C {lab_pin.sym} 800 -330 0 0 {name=l_CS_G lab=CSS}
C {lab_pin.sym} 800 -270 0 0 {name=l_CS_B lab=VSS}
C {nfet_03v3.sym} 1100 -300 0 0 {name=IEN model=nfet_03v3 W=2u L=0.35u nf=1 m=1}
C {lab_pin.sym} 1120 -330 0 0 {name=l_IEN_D lab=ENB}
C {lab_pin.sym} 1080 -300 0 0 {name=l_IEN_G lab=EN}
C {lab_pin.sym} 1120 -270 0 0 {name=l_IEN_S lab=VSS}
C {lab_pin.sym} 1120 -300 0 0 {name=l_IEN_B lab=VSS}
C {pfet_03v3.sym} 1400 -300 0 0 {name=IEP model=pfet_03v3 W=4u L=0.35u nf=1 m=1}
C {lab_pin.sym} 1420 -270 0 0 {name=l_IEP_D lab=ENB}
C {lab_pin.sym} 1380 -300 0 0 {name=l_IEP_G lab=EN}
C {lab_pin.sym} 1420 -330 0 0 {name=l_IEP_S lab=VDD33}
C {lab_pin.sym} 1420 -300 0 0 {name=l_IEP_B lab=VDD33}
C {nfet_03v3.sym} 1700 -300 0 0 {name=MRST model=nfet_03v3 W=2u L=0.5u nf=1 m=1}
C {lab_pin.sym} 1720 -330 0 0 {name=l_MRST_D lab=CSS}
C {lab_pin.sym} 1680 -300 0 0 {name=l_MRST_G lab=ENB}
C {lab_pin.sym} 1720 -270 0 0 {name=l_MRST_S lab=VSS}
C {lab_pin.sym} 1720 -300 0 0 {name=l_MRST_B lab=VSS}
C {nfet_03v3.sym} -400 -50 0 0 {name=MCD model=nfet_03v3 W=5u L=2u nf=1 m=1}
C {lab_pin.sym} -380 -80 0 0 {name=l_MCD_D lab=PB}
C {lab_pin.sym} -420 -50 0 0 {name=l_MCD_G lab=IBIAS}
C {lab_pin.sym} -380 -20 0 0 {name=l_MCD_S lab=VSS}
C {lab_pin.sym} -380 -50 0 0 {name=l_MCD_B lab=VSS}
C {pfet_03v3.sym} -100 -50 0 0 {name=MPB model=pfet_03v3 W=20u L=2u nf=1 m=1}
C {lab_pin.sym} -80 -20 0 0 {name=l_MPB_D lab=PB}
C {lab_pin.sym} -120 -50 0 0 {name=l_MPB_G lab=PB}
C {lab_pin.sym} -80 -80 0 0 {name=l_MPB_S lab=VDD33}
C {lab_pin.sym} -80 -50 0 0 {name=l_MPB_B lab=VDD33}
C {pfet_03v3.sym} 200 -50 0 0 {name=MPT model=pfet_03v3 W=20u L=2u nf=1 m=1}
C {lab_pin.sym} 220 -20 0 0 {name=l_MPT_D lab=TL}
C {lab_pin.sym} 180 -50 0 0 {name=l_MPT_G lab=PB}
C {lab_pin.sym} 220 -80 0 0 {name=l_MPT_S lab=VDD33}
C {lab_pin.sym} 220 -50 0 0 {name=l_MPT_B lab=VDD33}
C {pfet_03v3.sym} 500 -50 0 0 {name=MA model=pfet_03v3 W=16u L=1u nf=1 m=1}
C {lab_pin.sym} 520 -20 0 0 {name=l_MA_D lab=Y1}
C {lab_pin.sym} 480 -50 0 0 {name=l_MA_G lab=CSS}
C {lab_pin.sym} 520 -80 0 0 {name=l_MA_S lab=TL}
C {lab_pin.sym} 520 -50 0 0 {name=l_MA_B lab=VDD33}
C {pfet_03v3.sym} 800 -50 0 0 {name=MB model=pfet_03v3 W=16u L=1u nf=1 m=1}
C {lab_pin.sym} 820 -20 0 0 {name=l_MB_D lab=Y1}
C {lab_pin.sym} 780 -50 0 0 {name=l_MB_G lab=VBG}
C {lab_pin.sym} 820 -80 0 0 {name=l_MB_S lab=TL}
C {lab_pin.sym} 820 -50 0 0 {name=l_MB_B lab=VDD33}
C {pfet_03v3.sym} 1100 -50 0 0 {name=MF model=pfet_03v3 W=16u L=1u nf=1 m=1}
C {lab_pin.sym} 1120 -20 0 0 {name=l_MF_D lab=VREF_SS}
C {lab_pin.sym} 1080 -50 0 0 {name=l_MF_G lab=VREF_SS}
C {lab_pin.sym} 1120 -80 0 0 {name=l_MF_S lab=TL}
C {lab_pin.sym} 1120 -50 0 0 {name=l_MF_B lab=VDD33}
C {nfet_03v3.sym} 1400 -50 0 0 {name=ML1 model=nfet_03v3 W=4u L=1u nf=1 m=1}
C {lab_pin.sym} 1420 -80 0 0 {name=l_ML1_D lab=Y1}
C {lab_pin.sym} 1380 -50 0 0 {name=l_ML1_G lab=Y1}
C {lab_pin.sym} 1420 -20 0 0 {name=l_ML1_S lab=VSS}
C {lab_pin.sym} 1420 -50 0 0 {name=l_ML1_B lab=VSS}
C {nfet_03v3.sym} 1700 -50 0 0 {name=ML2 model=nfet_03v3 W=4u L=1u nf=1 m=1}
C {lab_pin.sym} 1720 -80 0 0 {name=l_ML2_D lab=VREF_SS}
C {lab_pin.sym} 1680 -50 0 0 {name=l_ML2_G lab=Y1}
C {lab_pin.sym} 1720 -20 0 0 {name=l_ML2_S lab=VSS}
C {lab_pin.sym} 1720 -50 0 0 {name=l_ML2_B lab=VSS}
