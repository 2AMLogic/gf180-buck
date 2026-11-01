v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {pwm_comp: voltage-mode PWM comparator + set/reset latch with cycle-by-cycle OCP reset} -600 -900 0 0 0.5 0.5 {}
T {Comparator OUT = (VC > RAMP).  PWM sets on the CLK pulse (ramp reset) and resets when RAMP crosses VC or OCP_TRIP asserts.} -600 -850 0 0 0.3 0.3 {}
T {Deviation recorded (design/README.md): sibling comparator_dut is a clocked StrongARM latch; a continuous PWM crossing needs a} -600 -820 0 0 0.3 0.3 {}
T {continuous-time stage, so a small single-stage comparator is drawn here rather than sizing a second sibling copy.} -600 -790 0 0 0.3 0.3 {}
T {NMOS-input pair: valid for VC and RAMP between ~1.1 V and ~2.2 V on the 3.3 V rail (checked in the smoke bench).} -600 -760 0 0 0.3 0.3 {}
C {ipin.sym} -900 -800 0 0 {name=p_VC lab=VC}
C {ipin.sym} -900 -760 0 0 {name=p_RAMP lab=RAMP}
C {ipin.sym} -900 -720 0 0 {name=p_CLK lab=CLK}
C {ipin.sym} -900 -680 0 0 {name=p_OCP_TRIP lab=OCP_TRIP}
C {ipin.sym} -900 -640 0 0 {name=p_IBIAS lab=IBIAS}
C {opin.sym} -900 -600 0 0 {name=p_PWM lab=PWM}
C {iopin.sym} -900 -560 0 0 {name=p_VDD33 lab=VDD33}
C {iopin.sym} -900 -520 0 0 {name=p_VSS lab=VSS}
C {nfet_03v3.sym} -400 -300 0 0 {name=MR model=nfet_03v3 W=10u L=2u nf=1 m=1}
C {lab_pin.sym} -380 -330 0 0 {name=l_MR_D lab=IBIAS}
C {lab_pin.sym} -420 -300 0 0 {name=l_MR_G lab=IBIAS}
C {lab_pin.sym} -380 -270 0 0 {name=l_MR_S lab=VSS}
C {lab_pin.sym} -380 -300 0 0 {name=l_MR_B lab=VSS}
C {nfet_03v3.sym} -100 -300 0 0 {name=CPT model=nfet_03v3 W=10u L=2u nf=1 m=1}
C {lab_pin.sym} -80 -330 0 0 {name=l_CPT_D lab=CP_t}
C {lab_pin.sym} -120 -300 0 0 {name=l_CPT_G lab=IBIAS}
C {lab_pin.sym} -80 -270 0 0 {name=l_CPT_S lab=VSS}
C {lab_pin.sym} -80 -300 0 0 {name=l_CPT_B lab=VSS}
C {nfet_03v3.sym} 200 -300 0 0 {name=CPM1 model=nfet_03v3 W=8u L=1u nf=1 m=1}
C {lab_pin.sym} 220 -330 0 0 {name=l_CPM1_D lab=CP_y1}
C {lab_pin.sym} 180 -300 0 0 {name=l_CPM1_G lab=VC}
C {lab_pin.sym} 220 -270 0 0 {name=l_CPM1_S lab=CP_t}
C {lab_pin.sym} 220 -300 0 0 {name=l_CPM1_B lab=VSS}
C {nfet_03v3.sym} 500 -300 0 0 {name=CPM2 model=nfet_03v3 W=8u L=1u nf=1 m=1}
C {lab_pin.sym} 520 -330 0 0 {name=l_CPM2_D lab=CP_y2}
C {lab_pin.sym} 480 -300 0 0 {name=l_CPM2_G lab=RAMP}
C {lab_pin.sym} 520 -270 0 0 {name=l_CPM2_S lab=CP_t}
C {lab_pin.sym} 520 -300 0 0 {name=l_CPM2_B lab=VSS}
C {pfet_03v3.sym} 800 -300 0 0 {name=CPL1 model=pfet_03v3 W=8u L=1u nf=1 m=1}
C {lab_pin.sym} 820 -270 0 0 {name=l_CPL1_D lab=CP_y1}
C {lab_pin.sym} 780 -300 0 0 {name=l_CPL1_G lab=CP_y1}
C {lab_pin.sym} 820 -330 0 0 {name=l_CPL1_S lab=VDD33}
C {lab_pin.sym} 820 -300 0 0 {name=l_CPL1_B lab=VDD33}
C {pfet_03v3.sym} 1100 -300 0 0 {name=CPL2 model=pfet_03v3 W=8u L=1u nf=1 m=1}
C {lab_pin.sym} 1120 -270 0 0 {name=l_CPL2_D lab=CP_y2}
C {lab_pin.sym} 1080 -300 0 0 {name=l_CPL2_G lab=CP_y1}
C {lab_pin.sym} 1120 -330 0 0 {name=l_CPL2_S lab=VDD33}
C {lab_pin.sym} 1120 -300 0 0 {name=l_CPL2_B lab=VDD33}
C {nfet_03v3.sym} 1400 -300 0 0 {name=CPI1N model=nfet_03v3 W=2u L=0.35u nf=1 m=1}
C {lab_pin.sym} 1420 -330 0 0 {name=l_CPI1N_D lab=CP_z}
C {lab_pin.sym} 1380 -300 0 0 {name=l_CPI1N_G lab=CP_y2}
C {lab_pin.sym} 1420 -270 0 0 {name=l_CPI1N_S lab=VSS}
C {lab_pin.sym} 1420 -300 0 0 {name=l_CPI1N_B lab=VSS}
C {pfet_03v3.sym} 1700 -300 0 0 {name=CPI1P model=pfet_03v3 W=4u L=0.35u nf=1 m=1}
C {lab_pin.sym} 1720 -270 0 0 {name=l_CPI1P_D lab=CP_z}
C {lab_pin.sym} 1680 -300 0 0 {name=l_CPI1P_G lab=CP_y2}
C {lab_pin.sym} 1720 -330 0 0 {name=l_CPI1P_S lab=VDD33}
C {lab_pin.sym} 1720 -300 0 0 {name=l_CPI1P_B lab=VDD33}
C {nfet_03v3.sym} -400 -50 0 0 {name=CPI2N model=nfet_03v3 W=2u L=0.35u nf=1 m=1}
C {lab_pin.sym} -380 -80 0 0 {name=l_CPI2N_D lab=CMP}
C {lab_pin.sym} -420 -50 0 0 {name=l_CPI2N_G lab=CP_z}
C {lab_pin.sym} -380 -20 0 0 {name=l_CPI2N_S lab=VSS}
C {lab_pin.sym} -380 -50 0 0 {name=l_CPI2N_B lab=VSS}
C {pfet_03v3.sym} -100 -50 0 0 {name=CPI2P model=pfet_03v3 W=4u L=0.35u nf=1 m=1}
C {lab_pin.sym} -80 -20 0 0 {name=l_CPI2P_D lab=CMP}
C {lab_pin.sym} -120 -50 0 0 {name=l_CPI2P_G lab=CP_z}
C {lab_pin.sym} -80 -80 0 0 {name=l_CPI2P_S lab=VDD33}
C {lab_pin.sym} -80 -50 0 0 {name=l_CPI2P_B lab=VDD33}
C {nfet_03v3.sym} 200 -50 0 0 {name=ION model=nfet_03v3 W=2u L=0.35u nf=1 m=1}
C {lab_pin.sym} 220 -80 0 0 {name=l_ION_D lab=OCPB}
C {lab_pin.sym} 180 -50 0 0 {name=l_ION_G lab=OCP_TRIP}
C {lab_pin.sym} 220 -20 0 0 {name=l_ION_S lab=VSS}
C {lab_pin.sym} 220 -50 0 0 {name=l_ION_B lab=VSS}
C {pfet_03v3.sym} 500 -50 0 0 {name=IOP model=pfet_03v3 W=4u L=0.35u nf=1 m=1}
C {lab_pin.sym} 520 -20 0 0 {name=l_IOP_D lab=OCPB}
C {lab_pin.sym} 480 -50 0 0 {name=l_IOP_G lab=OCP_TRIP}
C {lab_pin.sym} 520 -80 0 0 {name=l_IOP_S lab=VDD33}
C {lab_pin.sym} 520 -50 0 0 {name=l_IOP_B lab=VDD33}
C {nfet_03v3.sym} 800 -50 0 0 {name=NRNA model=nfet_03v3 W=4u L=0.35u nf=1 m=1}
C {lab_pin.sym} 820 -80 0 0 {name=l_NRNA_D lab=RST}
C {lab_pin.sym} 780 -50 0 0 {name=l_NRNA_G lab=CMP}
C {lab_pin.sym} 820 -20 0 0 {name=l_NRNA_S lab=NR_n}
C {lab_pin.sym} 820 -50 0 0 {name=l_NRNA_B lab=VSS}
C {nfet_03v3.sym} 1100 -50 0 0 {name=NRNB model=nfet_03v3 W=4u L=0.35u nf=1 m=1}
C {lab_pin.sym} 1120 -80 0 0 {name=l_NRNB_D lab=NR_n}
C {lab_pin.sym} 1080 -50 0 0 {name=l_NRNB_G lab=OCPB}
C {lab_pin.sym} 1120 -20 0 0 {name=l_NRNB_S lab=VSS}
C {lab_pin.sym} 1120 -50 0 0 {name=l_NRNB_B lab=VSS}
C {pfet_03v3.sym} 1400 -50 0 0 {name=NRPA model=pfet_03v3 W=4u L=0.35u nf=1 m=1}
C {lab_pin.sym} 1420 -20 0 0 {name=l_NRPA_D lab=RST}
C {lab_pin.sym} 1380 -50 0 0 {name=l_NRPA_G lab=CMP}
C {lab_pin.sym} 1420 -80 0 0 {name=l_NRPA_S lab=VDD33}
C {lab_pin.sym} 1420 -50 0 0 {name=l_NRPA_B lab=VDD33}
C {pfet_03v3.sym} 1700 -50 0 0 {name=NRPB model=pfet_03v3 W=4u L=0.35u nf=1 m=1}
C {lab_pin.sym} 1720 -20 0 0 {name=l_NRPB_D lab=RST}
C {lab_pin.sym} 1680 -50 0 0 {name=l_NRPB_G lab=OCPB}
C {lab_pin.sym} 1720 -80 0 0 {name=l_NRPB_S lab=VDD33}
C {lab_pin.sym} 1720 -50 0 0 {name=l_NRPB_B lab=VDD33}
C {nfet_03v3.sym} -400 200 0 0 {name=L1NA model=nfet_03v3 W=2u L=0.35u nf=1 m=1}
C {lab_pin.sym} -380 170 0 0 {name=l_L1NA_D lab=Q}
C {lab_pin.sym} -420 200 0 0 {name=l_L1NA_G lab=RST}
C {lab_pin.sym} -380 230 0 0 {name=l_L1NA_S lab=VSS}
C {lab_pin.sym} -380 200 0 0 {name=l_L1NA_B lab=VSS}
C {nfet_03v3.sym} -100 200 0 0 {name=L1NB model=nfet_03v3 W=2u L=0.35u nf=1 m=1}
C {lab_pin.sym} -80 170 0 0 {name=l_L1NB_D lab=Q}
C {lab_pin.sym} -120 200 0 0 {name=l_L1NB_G lab=QB}
C {lab_pin.sym} -80 230 0 0 {name=l_L1NB_S lab=VSS}
C {lab_pin.sym} -80 200 0 0 {name=l_L1NB_B lab=VSS}
C {pfet_03v3.sym} 200 200 0 0 {name=L1PA model=pfet_03v3 W=8u L=0.35u nf=1 m=1}
C {lab_pin.sym} 220 230 0 0 {name=l_L1PA_D lab=L1_p}
C {lab_pin.sym} 180 200 0 0 {name=l_L1PA_G lab=RST}
C {lab_pin.sym} 220 170 0 0 {name=l_L1PA_S lab=VDD33}
C {lab_pin.sym} 220 200 0 0 {name=l_L1PA_B lab=VDD33}
C {pfet_03v3.sym} 500 200 0 0 {name=L1PB model=pfet_03v3 W=8u L=0.35u nf=1 m=1}
C {lab_pin.sym} 520 230 0 0 {name=l_L1PB_D lab=Q}
C {lab_pin.sym} 480 200 0 0 {name=l_L1PB_G lab=QB}
C {lab_pin.sym} 520 170 0 0 {name=l_L1PB_S lab=L1_p}
C {lab_pin.sym} 520 200 0 0 {name=l_L1PB_B lab=VDD33}
C {nfet_03v3.sym} 800 200 0 0 {name=L2NA model=nfet_03v3 W=2u L=0.35u nf=1 m=1}
C {lab_pin.sym} 820 170 0 0 {name=l_L2NA_D lab=QB}
C {lab_pin.sym} 780 200 0 0 {name=l_L2NA_G lab=CLK}
C {lab_pin.sym} 820 230 0 0 {name=l_L2NA_S lab=VSS}
C {lab_pin.sym} 820 200 0 0 {name=l_L2NA_B lab=VSS}
C {nfet_03v3.sym} 1100 200 0 0 {name=L2NB model=nfet_03v3 W=2u L=0.35u nf=1 m=1}
C {lab_pin.sym} 1120 170 0 0 {name=l_L2NB_D lab=QB}
C {lab_pin.sym} 1080 200 0 0 {name=l_L2NB_G lab=Q}
C {lab_pin.sym} 1120 230 0 0 {name=l_L2NB_S lab=VSS}
C {lab_pin.sym} 1120 200 0 0 {name=l_L2NB_B lab=VSS}
C {pfet_03v3.sym} 1400 200 0 0 {name=L2PA model=pfet_03v3 W=8u L=0.35u nf=1 m=1}
C {lab_pin.sym} 1420 230 0 0 {name=l_L2PA_D lab=L2_p}
C {lab_pin.sym} 1380 200 0 0 {name=l_L2PA_G lab=CLK}
C {lab_pin.sym} 1420 170 0 0 {name=l_L2PA_S lab=VDD33}
C {lab_pin.sym} 1420 200 0 0 {name=l_L2PA_B lab=VDD33}
C {pfet_03v3.sym} 1700 200 0 0 {name=L2PB model=pfet_03v3 W=8u L=0.35u nf=1 m=1}
C {lab_pin.sym} 1720 230 0 0 {name=l_L2PB_D lab=QB}
C {lab_pin.sym} 1680 200 0 0 {name=l_L2PB_G lab=Q}
C {lab_pin.sym} 1720 170 0 0 {name=l_L2PB_S lab=L2_p}
C {lab_pin.sym} 1720 200 0 0 {name=l_L2PB_B lab=VDD33}
C {nfet_03v3.sym} -400 450 0 0 {name=IQ1N model=nfet_03v3 W=2u L=0.35u nf=1 m=1}
C {lab_pin.sym} -380 420 0 0 {name=l_IQ1N_D lab=QN}
C {lab_pin.sym} -420 450 0 0 {name=l_IQ1N_G lab=Q}
C {lab_pin.sym} -380 480 0 0 {name=l_IQ1N_S lab=VSS}
C {lab_pin.sym} -380 450 0 0 {name=l_IQ1N_B lab=VSS}
C {pfet_03v3.sym} -100 450 0 0 {name=IQ1P model=pfet_03v3 W=4u L=0.35u nf=1 m=1}
C {lab_pin.sym} -80 480 0 0 {name=l_IQ1P_D lab=QN}
C {lab_pin.sym} -120 450 0 0 {name=l_IQ1P_G lab=Q}
C {lab_pin.sym} -80 420 0 0 {name=l_IQ1P_S lab=VDD33}
C {lab_pin.sym} -80 450 0 0 {name=l_IQ1P_B lab=VDD33}
C {nfet_03v3.sym} 200 450 0 0 {name=IQ2N model=nfet_03v3 W=4u L=0.35u nf=1 m=1}
C {lab_pin.sym} 220 420 0 0 {name=l_IQ2N_D lab=PWM}
C {lab_pin.sym} 180 450 0 0 {name=l_IQ2N_G lab=QN}
C {lab_pin.sym} 220 480 0 0 {name=l_IQ2N_S lab=VSS}
C {lab_pin.sym} 220 450 0 0 {name=l_IQ2N_B lab=VSS}
C {pfet_03v3.sym} 500 450 0 0 {name=IQ2P model=pfet_03v3 W=8u L=0.35u nf=1 m=1}
C {lab_pin.sym} 520 480 0 0 {name=l_IQ2P_D lab=PWM}
C {lab_pin.sym} 480 450 0 0 {name=l_IQ2P_G lab=QN}
C {lab_pin.sym} 520 420 0 0 {name=l_IQ2P_S lab=VDD33}
C {lab_pin.sym} 520 450 0 0 {name=l_IQ2P_B lab=VDD33}
