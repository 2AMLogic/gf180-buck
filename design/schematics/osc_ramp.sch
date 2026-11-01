v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {osc_ramp: 2 MHz relaxation oscillator + PWM sawtooth ramp (R7, R6 forced PWM)} -600 -900 0 0 0.5 0.5 {}
T {Charge: IBIAS (nom. 12 uA into the pin) -> NMOS mirror x0.6 (7.2 uA) -> PMOS mirror x1 -> RAMP node (current source into C).} -600 -850 0 0 0.3 0.3 {}
T {Schmitt on RAMP; its output resets RAMP through MDIS and is the CLK pulse (rising = ramp reset = cycle start).} -600 -820 0 0 0.3 0.3 {}
T {Trim: TRIM<2:0> switch binary-weighted MIM caps onto RAMP (single-point trim at test, spec R7).} -600 -790 0 0 0.3 0.3 {}
T {Supply: 3.3 V control rail (decision record 0003). T = C*dV/I: depends on C, IBIAS and the Schmitt window.} -600 -760 0 0 0.3 0.3 {}
T {Sibling gf180-rcosc is kept, not adopted (reuse.lock.json): topology idea only, nothing copied.} -600 -730 0 0 0.3 0.3 {}
C {ipin.sym} -900 -800 0 0 {name=p_IBIAS lab=IBIAS}
C {ipin.sym} -900 -760 0 0 {name=p_TRIM0 lab=TRIM0}
C {ipin.sym} -900 -720 0 0 {name=p_TRIM1 lab=TRIM1}
C {ipin.sym} -900 -680 0 0 {name=p_TRIM2 lab=TRIM2}
C {opin.sym} -900 -640 0 0 {name=p_CLK lab=CLK}
C {opin.sym} -900 -600 0 0 {name=p_RAMP lab=RAMP}
C {iopin.sym} -900 -560 0 0 {name=p_VDD33 lab=VDD33}
C {iopin.sym} -900 -520 0 0 {name=p_VSS lab=VSS}
C {nfet_03v3.sym} -400 -300 0 0 {name=MN0 model=nfet_03v3 W=10u L=2u nf=1 m=1}
C {lab_pin.sym} -380 -330 0 0 {name=l_MN0_D lab=IBIAS}
C {lab_pin.sym} -420 -300 0 0 {name=l_MN0_G lab=IBIAS}
C {lab_pin.sym} -380 -270 0 0 {name=l_MN0_S lab=VSS}
C {lab_pin.sym} -380 -300 0 0 {name=l_MN0_B lab=VSS}
C {nfet_03v3.sym} -100 -300 0 0 {name=MN1 model=nfet_03v3 W=6u L=2u nf=1 m=1}
C {lab_pin.sym} -80 -330 0 0 {name=l_MN1_D lab=PD}
C {lab_pin.sym} -120 -300 0 0 {name=l_MN1_G lab=IBIAS}
C {lab_pin.sym} -80 -270 0 0 {name=l_MN1_S lab=VSS}
C {lab_pin.sym} -80 -300 0 0 {name=l_MN1_B lab=VSS}
C {pfet_03v3.sym} 200 -300 0 0 {name=MP0 model=pfet_03v3 W=20u L=2u nf=1 m=1}
C {lab_pin.sym} 220 -270 0 0 {name=l_MP0_D lab=PD}
C {lab_pin.sym} 180 -300 0 0 {name=l_MP0_G lab=PD}
C {lab_pin.sym} 220 -330 0 0 {name=l_MP0_S lab=VDD33}
C {lab_pin.sym} 220 -300 0 0 {name=l_MP0_B lab=VDD33}
C {pfet_03v3.sym} 500 -300 0 0 {name=MP1 model=pfet_03v3 W=20u L=2u nf=1 m=1}
C {lab_pin.sym} 520 -270 0 0 {name=l_MP1_D lab=RAMP}
C {lab_pin.sym} 480 -300 0 0 {name=l_MP1_G lab=PD}
C {lab_pin.sym} 520 -330 0 0 {name=l_MP1_S lab=VDD33}
C {lab_pin.sym} 520 -300 0 0 {name=l_MP1_B lab=VDD33}
C {cap_mim_2f0fF.sym} 800 -300 0 0 {name=CR model=cap_mim_2f0fF W=45u L=45u m=1}
C {lab_pin.sym} 800 -330 0 0 {name=l_CR_G lab=RAMP}
C {lab_pin.sym} 800 -270 0 0 {name=l_CR_B lab=VSS}
C {cap_mim_2f0fF.sym} 1100 -300 0 0 {name=CT0 model=cap_mim_2f0fF W=15u L=15u m=1}
C {lab_pin.sym} 1100 -330 0 0 {name=l_CT0_G lab=RAMP}
C {lab_pin.sym} 1100 -270 0 0 {name=l_CT0_B lab=CTB0}
C {nfet_03v3.sym} 1400 -300 0 0 {name=MT0 model=nfet_03v3 W=8u L=0.35u nf=1 m=1}
C {lab_pin.sym} 1420 -330 0 0 {name=l_MT0_D lab=CTB0}
C {lab_pin.sym} 1380 -300 0 0 {name=l_MT0_G lab=TRIM0}
C {lab_pin.sym} 1420 -270 0 0 {name=l_MT0_S lab=VSS}
C {lab_pin.sym} 1420 -300 0 0 {name=l_MT0_B lab=VSS}
C {cap_mim_2f0fF.sym} 1700 -300 0 0 {name=CT1 model=cap_mim_2f0fF W=15u L=30u m=1}
C {lab_pin.sym} 1700 -330 0 0 {name=l_CT1_G lab=RAMP}
C {lab_pin.sym} 1700 -270 0 0 {name=l_CT1_B lab=CTB1}
C {nfet_03v3.sym} -400 -50 0 0 {name=MT1 model=nfet_03v3 W=8u L=0.35u nf=1 m=1}
C {lab_pin.sym} -380 -80 0 0 {name=l_MT1_D lab=CTB1}
C {lab_pin.sym} -420 -50 0 0 {name=l_MT1_G lab=TRIM1}
C {lab_pin.sym} -380 -20 0 0 {name=l_MT1_S lab=VSS}
C {lab_pin.sym} -380 -50 0 0 {name=l_MT1_B lab=VSS}
C {cap_mim_2f0fF.sym} -100 -50 0 0 {name=CT2 model=cap_mim_2f0fF W=15u L=60u m=1}
C {lab_pin.sym} -100 -80 0 0 {name=l_CT2_G lab=RAMP}
C {lab_pin.sym} -100 -20 0 0 {name=l_CT2_B lab=CTB2}
C {nfet_03v3.sym} 200 -50 0 0 {name=MT2 model=nfet_03v3 W=8u L=0.35u nf=1 m=1}
C {lab_pin.sym} 220 -80 0 0 {name=l_MT2_D lab=CTB2}
C {lab_pin.sym} 180 -50 0 0 {name=l_MT2_G lab=TRIM2}
C {lab_pin.sym} 220 -20 0 0 {name=l_MT2_S lab=VSS}
C {lab_pin.sym} 220 -50 0 0 {name=l_MT2_B lab=VSS}
C {pfet_03v3.sym} 500 -50 0 0 {name=SCP1 model=pfet_03v3 W=8u L=0.5u nf=1 m=1}
C {lab_pin.sym} 520 -20 0 0 {name=l_SCP1_D lab=SC_pa}
C {lab_pin.sym} 480 -50 0 0 {name=l_SCP1_G lab=RAMP}
C {lab_pin.sym} 520 -80 0 0 {name=l_SCP1_S lab=VDD33}
C {lab_pin.sym} 520 -50 0 0 {name=l_SCP1_B lab=VDD33}
C {pfet_03v3.sym} 800 -50 0 0 {name=SCP2 model=pfet_03v3 W=8u L=0.5u nf=1 m=1}
C {lab_pin.sym} 820 -20 0 0 {name=l_SCP2_D lab=SCO}
C {lab_pin.sym} 780 -50 0 0 {name=l_SCP2_G lab=RAMP}
C {lab_pin.sym} 820 -80 0 0 {name=l_SCP2_S lab=SC_pa}
C {lab_pin.sym} 820 -50 0 0 {name=l_SCP2_B lab=VDD33}
C {nfet_03v3.sym} 1100 -50 0 0 {name=SCN2 model=nfet_03v3 W=4u L=0.5u nf=1 m=1}
C {lab_pin.sym} 1120 -80 0 0 {name=l_SCN2_D lab=SCO}
C {lab_pin.sym} 1080 -50 0 0 {name=l_SCN2_G lab=RAMP}
C {lab_pin.sym} 1120 -20 0 0 {name=l_SCN2_S lab=SC_na}
C {lab_pin.sym} 1120 -50 0 0 {name=l_SCN2_B lab=VSS}
C {nfet_03v3.sym} 1400 -50 0 0 {name=SCN1 model=nfet_03v3 W=4u L=0.5u nf=1 m=1}
C {lab_pin.sym} 1420 -80 0 0 {name=l_SCN1_D lab=SC_na}
C {lab_pin.sym} 1380 -50 0 0 {name=l_SCN1_G lab=RAMP}
C {lab_pin.sym} 1420 -20 0 0 {name=l_SCN1_S lab=VSS}
C {lab_pin.sym} 1420 -50 0 0 {name=l_SCN1_B lab=VSS}
C {nfet_03v3.sym} 1700 -50 0 0 {name=SCNF model=nfet_03v3 W=2u L=0.5u nf=1 m=1}
C {lab_pin.sym} 1720 -80 0 0 {name=l_SCNF_D lab=VDD33}
C {lab_pin.sym} 1680 -50 0 0 {name=l_SCNF_G lab=SCO}
C {lab_pin.sym} 1720 -20 0 0 {name=l_SCNF_S lab=SC_na}
C {lab_pin.sym} 1720 -50 0 0 {name=l_SCNF_B lab=VSS}
C {pfet_03v3.sym} -400 200 0 0 {name=SCPF model=pfet_03v3 W=4u L=0.5u nf=1 m=1}
C {lab_pin.sym} -380 230 0 0 {name=l_SCPF_D lab=VSS}
C {lab_pin.sym} -420 200 0 0 {name=l_SCPF_G lab=SCO}
C {lab_pin.sym} -380 170 0 0 {name=l_SCPF_S lab=SC_pa}
C {lab_pin.sym} -380 200 0 0 {name=l_SCPF_B lab=VDD33}
C {nfet_03v3.sym} -100 200 0 0 {name=IV1N model=nfet_03v3 W=2u L=0.35u nf=1 m=1}
C {lab_pin.sym} -80 170 0 0 {name=l_IV1N_D lab=DIS}
C {lab_pin.sym} -120 200 0 0 {name=l_IV1N_G lab=SCO}
C {lab_pin.sym} -80 230 0 0 {name=l_IV1N_S lab=VSS}
C {lab_pin.sym} -80 200 0 0 {name=l_IV1N_B lab=VSS}
C {pfet_03v3.sym} 200 200 0 0 {name=IV1P model=pfet_03v3 W=4u L=0.35u nf=1 m=1}
C {lab_pin.sym} 220 230 0 0 {name=l_IV1P_D lab=DIS}
C {lab_pin.sym} 180 200 0 0 {name=l_IV1P_G lab=SCO}
C {lab_pin.sym} 220 170 0 0 {name=l_IV1P_S lab=VDD33}
C {lab_pin.sym} 220 200 0 0 {name=l_IV1P_B lab=VDD33}
C {nfet_03v3.sym} 500 200 0 0 {name=IV2N model=nfet_03v3 W=4u L=0.35u nf=1 m=1}
C {lab_pin.sym} 520 170 0 0 {name=l_IV2N_D lab=CKB}
C {lab_pin.sym} 480 200 0 0 {name=l_IV2N_G lab=DIS}
C {lab_pin.sym} 520 230 0 0 {name=l_IV2N_S lab=VSS}
C {lab_pin.sym} 520 200 0 0 {name=l_IV2N_B lab=VSS}
C {pfet_03v3.sym} 800 200 0 0 {name=IV2P model=pfet_03v3 W=8u L=0.35u nf=1 m=1}
C {lab_pin.sym} 820 230 0 0 {name=l_IV2P_D lab=CKB}
C {lab_pin.sym} 780 200 0 0 {name=l_IV2P_G lab=DIS}
C {lab_pin.sym} 820 170 0 0 {name=l_IV2P_S lab=VDD33}
C {lab_pin.sym} 820 200 0 0 {name=l_IV2P_B lab=VDD33}
C {nfet_03v3.sym} 1100 200 0 0 {name=IV3N model=nfet_03v3 W=8u L=0.35u nf=1 m=1}
C {lab_pin.sym} 1120 170 0 0 {name=l_IV3N_D lab=CLK}
C {lab_pin.sym} 1080 200 0 0 {name=l_IV3N_G lab=CKB}
C {lab_pin.sym} 1120 230 0 0 {name=l_IV3N_S lab=VSS}
C {lab_pin.sym} 1120 200 0 0 {name=l_IV3N_B lab=VSS}
C {pfet_03v3.sym} 1400 200 0 0 {name=IV3P model=pfet_03v3 W=16u L=0.35u nf=1 m=1}
C {lab_pin.sym} 1420 230 0 0 {name=l_IV3P_D lab=CLK}
C {lab_pin.sym} 1380 200 0 0 {name=l_IV3P_G lab=CKB}
C {lab_pin.sym} 1420 170 0 0 {name=l_IV3P_S lab=VDD33}
C {lab_pin.sym} 1420 200 0 0 {name=l_IV3P_B lab=VDD33}
C {nfet_03v3.sym} 1700 200 0 0 {name=MDIS model=nfet_03v3 W=2u L=1u nf=1 m=1}
C {lab_pin.sym} 1720 170 0 0 {name=l_MDIS_D lab=RAMP}
C {lab_pin.sym} 1680 200 0 0 {name=l_MDIS_G lab=DIS}
C {lab_pin.sym} 1720 230 0 0 {name=l_MDIS_S lab=VSS}
C {lab_pin.sym} 1720 200 0 0 {name=l_MDIS_B lab=VSS}
