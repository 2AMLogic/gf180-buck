v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {ocp_sense: Ron-sense cycle-by-cycle current limit on the high-side switch (R16, R6 no-trip)} -600 -900 0 0 0.5 0.5 {}
T {Senses VIN - SW across the high-side pFET while it conducts.  NMOS pair (thick 6 V) with gates at SW and at VTHP = VIN - Itrip*RT;} -600 -850 0 0 0.3 0.3 {}
T {branch currents are mirrored from the VIN domain into resistors on the 3.3 V rail; a PMOS-input comparator compares them.} -600 -820 0 0 0.3 0.3 {}
T {Reverse (negative) inductor current makes SW > VIN, so the pair never trips (R6).  TRIP = raw & HS_ON & blank-delayed HS_ON.} -600 -790 0 0 0.3 0.3 {}
T {Trip current = Vtrip / Ron_HS: inherits Ron's PVT window (3:1), a die-protection threshold, not a precision limit (R16).} -600 -760 0 0 0.3 0.3 {}
T {Deviation recorded: sibling comparator_dut cannot take SW/VIN inputs (3.3 V part) and is clocked; the VIN-domain front end is new.} -600 -730 0 0 0.3 0.3 {}
C {ipin.sym} -900 -800 0 0 {name=p_SW lab=SW}
C {ipin.sym} -900 -760 0 0 {name=p_HS_ON lab=HS_ON}
C {ipin.sym} -900 -720 0 0 {name=p_IBIAS lab=IBIAS}
C {opin.sym} -900 -680 0 0 {name=p_TRIP lab=TRIP}
C {iopin.sym} -900 -640 0 0 {name=p_VIN lab=VIN}
C {iopin.sym} -900 -600 0 0 {name=p_VDD33 lab=VDD33}
C {iopin.sym} -900 -560 0 0 {name=p_VSS lab=VSS}
C {nfet_06v0.sym} -400 -300 0 0 {name=MR model=nfet_06v0 W=10u L=2u nf=1 m=1}
C {lab_pin.sym} -380 -330 0 0 {name=l_MR_D lab=IBIAS}
C {lab_pin.sym} -420 -300 0 0 {name=l_MR_G lab=IBIAS}
C {lab_pin.sym} -380 -270 0 0 {name=l_MR_S lab=VSS}
C {lab_pin.sym} -380 -300 0 0 {name=l_MR_B lab=VSS}
C {nfet_06v0.sym} -100 -300 0 0 {name=MTAIL model=nfet_06v0 W=10u L=2u nf=1 m=1}
C {lab_pin.sym} -80 -330 0 0 {name=l_MTAIL_D lab=TAIL}
C {lab_pin.sym} -120 -300 0 0 {name=l_MTAIL_G lab=IBIAS}
C {lab_pin.sym} -80 -270 0 0 {name=l_MTAIL_S lab=VSS}
C {lab_pin.sym} -80 -300 0 0 {name=l_MTAIL_B lab=VSS}
C {nfet_06v0.sym} 200 -300 0 0 {name=MTRIP model=nfet_06v0 W=5u L=2u nf=1 m=1}
C {lab_pin.sym} 220 -330 0 0 {name=l_MTRIP_D lab=VTHP}
C {lab_pin.sym} 180 -300 0 0 {name=l_MTRIP_G lab=IBIAS}
C {lab_pin.sym} 220 -270 0 0 {name=l_MTRIP_S lab=VSS}
C {lab_pin.sym} 220 -300 0 0 {name=l_MTRIP_B lab=VSS}
C {ppolyf_u.sym} 500 -300 0 0 {name=RT model=ppolyf_u W=2u L=120u m=1}
C {lab_pin.sym} 500 -330 0 0 {name=l_RT_P lab=VIN}
C {lab_pin.sym} 500 -270 0 0 {name=l_RT_M lab=VTHP}
C {lab_pin.sym} 480 -300 0 0 {name=l_RT_B lab=VSS}
C {nfet_06v0.sym} 800 -300 0 0 {name=MS model=nfet_06v0 W=20u L=1u nf=1 m=1}
C {lab_pin.sym} 820 -330 0 0 {name=l_MS_D lab=D1}
C {lab_pin.sym} 780 -300 0 0 {name=l_MS_G lab=SW}
C {lab_pin.sym} 820 -270 0 0 {name=l_MS_S lab=TAIL}
C {lab_pin.sym} 820 -300 0 0 {name=l_MS_B lab=VSS}
C {nfet_06v0.sym} 1100 -300 0 0 {name=MT model=nfet_06v0 W=20u L=1u nf=1 m=1}
C {lab_pin.sym} 1120 -330 0 0 {name=l_MT_D lab=D2}
C {lab_pin.sym} 1080 -300 0 0 {name=l_MT_G lab=VTHP}
C {lab_pin.sym} 1120 -270 0 0 {name=l_MT_S lab=TAIL}
C {lab_pin.sym} 1120 -300 0 0 {name=l_MT_B lab=VSS}
C {pfet_06v0.sym} 1400 -300 0 0 {name=MP1 model=pfet_06v0 W=10u L=2u nf=1 m=1}
C {lab_pin.sym} 1420 -270 0 0 {name=l_MP1_D lab=D1}
C {lab_pin.sym} 1380 -300 0 0 {name=l_MP1_G lab=D1}
C {lab_pin.sym} 1420 -330 0 0 {name=l_MP1_S lab=VIN}
C {lab_pin.sym} 1420 -300 0 0 {name=l_MP1_B lab=VIN}
C {pfet_06v0.sym} 1700 -300 0 0 {name=MP2 model=pfet_06v0 W=10u L=2u nf=1 m=1}
C {lab_pin.sym} 1720 -270 0 0 {name=l_MP2_D lab=D2}
C {lab_pin.sym} 1680 -300 0 0 {name=l_MP2_G lab=D2}
C {lab_pin.sym} 1720 -330 0 0 {name=l_MP2_S lab=VIN}
C {lab_pin.sym} 1720 -300 0 0 {name=l_MP2_B lab=VIN}
C {pfet_06v0.sym} -400 -50 0 0 {name=MC1 model=pfet_06v0 W=10u L=2u nf=1 m=1}
C {lab_pin.sym} -380 -20 0 0 {name=l_MC1_D lab=V1}
C {lab_pin.sym} -420 -50 0 0 {name=l_MC1_G lab=D1}
C {lab_pin.sym} -380 -80 0 0 {name=l_MC1_S lab=VIN}
C {lab_pin.sym} -380 -50 0 0 {name=l_MC1_B lab=VIN}
C {pfet_06v0.sym} -100 -50 0 0 {name=MC2 model=pfet_06v0 W=10u L=2u nf=1 m=1}
C {lab_pin.sym} -80 -20 0 0 {name=l_MC2_D lab=V2}
C {lab_pin.sym} -120 -50 0 0 {name=l_MC2_G lab=D2}
C {lab_pin.sym} -80 -80 0 0 {name=l_MC2_S lab=VIN}
C {lab_pin.sym} -80 -50 0 0 {name=l_MC2_B lab=VIN}
C {ppolyf_u.sym} 200 -50 0 0 {name=R1 model=ppolyf_u W=2u L=250u m=1}
C {lab_pin.sym} 200 -80 0 0 {name=l_R1_P lab=V1}
C {lab_pin.sym} 200 -20 0 0 {name=l_R1_M lab=VSS}
C {lab_pin.sym} 180 -50 0 0 {name=l_R1_B lab=VSS}
C {ppolyf_u.sym} 500 -50 0 0 {name=R2 model=ppolyf_u W=2u L=250u m=1}
C {lab_pin.sym} 500 -80 0 0 {name=l_R2_P lab=V2}
C {lab_pin.sym} 500 -20 0 0 {name=l_R2_M lab=VSS}
C {lab_pin.sym} 480 -50 0 0 {name=l_R2_B lab=VSS}
C {nfet_06v0.sym} 800 -50 0 0 {name=MNC model=nfet_06v0 W=5u L=2u nf=1 m=1}
C {lab_pin.sym} 820 -80 0 0 {name=l_MNC_D lab=PB}
C {lab_pin.sym} 780 -50 0 0 {name=l_MNC_G lab=IBIAS}
C {lab_pin.sym} 820 -20 0 0 {name=l_MNC_S lab=VSS}
C {lab_pin.sym} 820 -50 0 0 {name=l_MNC_B lab=VSS}
C {pfet_03v3.sym} 1100 -50 0 0 {name=MPB model=pfet_03v3 W=20u L=2u nf=1 m=1}
C {lab_pin.sym} 1120 -20 0 0 {name=l_MPB_D lab=PB}
C {lab_pin.sym} 1080 -50 0 0 {name=l_MPB_G lab=PB}
C {lab_pin.sym} 1120 -80 0 0 {name=l_MPB_S lab=VDD33}
C {lab_pin.sym} 1120 -50 0 0 {name=l_MPB_B lab=VDD33}
C {pfet_03v3.sym} 1400 -50 0 0 {name=CCT model=pfet_03v3 W=20u L=2u nf=1 m=1}
C {lab_pin.sym} 1420 -20 0 0 {name=l_CCT_D lab=CC_t}
C {lab_pin.sym} 1380 -50 0 0 {name=l_CCT_G lab=PB}
C {lab_pin.sym} 1420 -80 0 0 {name=l_CCT_S lab=VDD33}
C {lab_pin.sym} 1420 -50 0 0 {name=l_CCT_B lab=VDD33}
C {pfet_03v3.sym} 1700 -50 0 0 {name=CCM1 model=pfet_03v3 W=16u L=1u nf=1 m=1}
C {lab_pin.sym} 1720 -20 0 0 {name=l_CCM1_D lab=CC_y1}
C {lab_pin.sym} 1680 -50 0 0 {name=l_CCM1_G lab=V2}
C {lab_pin.sym} 1720 -80 0 0 {name=l_CCM1_S lab=CC_t}
C {lab_pin.sym} 1720 -50 0 0 {name=l_CCM1_B lab=VDD33}
C {pfet_03v3.sym} -400 200 0 0 {name=CCM2 model=pfet_03v3 W=16u L=1u nf=1 m=1}
C {lab_pin.sym} -380 230 0 0 {name=l_CCM2_D lab=CC_y2}
C {lab_pin.sym} -420 200 0 0 {name=l_CCM2_G lab=V1}
C {lab_pin.sym} -380 170 0 0 {name=l_CCM2_S lab=CC_t}
C {lab_pin.sym} -380 200 0 0 {name=l_CCM2_B lab=VDD33}
C {nfet_03v3.sym} -100 200 0 0 {name=CCL1 model=nfet_03v3 W=4u L=1u nf=1 m=1}
C {lab_pin.sym} -80 170 0 0 {name=l_CCL1_D lab=CC_y1}
C {lab_pin.sym} -120 200 0 0 {name=l_CCL1_G lab=CC_y1}
C {lab_pin.sym} -80 230 0 0 {name=l_CCL1_S lab=VSS}
C {lab_pin.sym} -80 200 0 0 {name=l_CCL1_B lab=VSS}
C {nfet_03v3.sym} 200 200 0 0 {name=CCL2 model=nfet_03v3 W=4u L=1u nf=1 m=1}
C {lab_pin.sym} 220 170 0 0 {name=l_CCL2_D lab=CC_y2}
C {lab_pin.sym} 180 200 0 0 {name=l_CCL2_G lab=CC_y1}
C {lab_pin.sym} 220 230 0 0 {name=l_CCL2_S lab=VSS}
C {lab_pin.sym} 220 200 0 0 {name=l_CCL2_B lab=VSS}
C {nfet_03v3.sym} 500 200 0 0 {name=CCI1N model=nfet_03v3 W=2u L=0.35u nf=1 m=1}
C {lab_pin.sym} 520 170 0 0 {name=l_CCI1N_D lab=CC_z}
C {lab_pin.sym} 480 200 0 0 {name=l_CCI1N_G lab=CC_y2}
C {lab_pin.sym} 520 230 0 0 {name=l_CCI1N_S lab=VSS}
C {lab_pin.sym} 520 200 0 0 {name=l_CCI1N_B lab=VSS}
C {pfet_03v3.sym} 800 200 0 0 {name=CCI1P model=pfet_03v3 W=4u L=0.35u nf=1 m=1}
C {lab_pin.sym} 820 230 0 0 {name=l_CCI1P_D lab=CC_z}
C {lab_pin.sym} 780 200 0 0 {name=l_CCI1P_G lab=CC_y2}
C {lab_pin.sym} 820 170 0 0 {name=l_CCI1P_S lab=VDD33}
C {lab_pin.sym} 820 200 0 0 {name=l_CCI1P_B lab=VDD33}
C {nfet_03v3.sym} 1100 200 0 0 {name=CCI2N model=nfet_03v3 W=2u L=0.35u nf=1 m=1}
C {lab_pin.sym} 1120 170 0 0 {name=l_CCI2N_D lab=RAW}
C {lab_pin.sym} 1080 200 0 0 {name=l_CCI2N_G lab=CC_z}
C {lab_pin.sym} 1120 230 0 0 {name=l_CCI2N_S lab=VSS}
C {lab_pin.sym} 1120 200 0 0 {name=l_CCI2N_B lab=VSS}
C {pfet_03v3.sym} 1400 200 0 0 {name=CCI2P model=pfet_03v3 W=4u L=0.35u nf=1 m=1}
C {lab_pin.sym} 1420 230 0 0 {name=l_CCI2P_D lab=RAW}
C {lab_pin.sym} 1380 200 0 0 {name=l_CCI2P_G lab=CC_z}
C {lab_pin.sym} 1420 170 0 0 {name=l_CCI2P_S lab=VDD33}
C {lab_pin.sym} 1420 200 0 0 {name=l_CCI2P_B lab=VDD33}
C {ppolyf_u.sym} 1700 200 0 0 {name=RB model=ppolyf_u W=2u L=300u m=1}
C {lab_pin.sym} 1700 170 0 0 {name=l_RB_P lab=HS_ON}
C {lab_pin.sym} 1700 230 0 0 {name=l_RB_M lab=BLR}
C {lab_pin.sym} 1680 200 0 0 {name=l_RB_B lab=VSS}
C {cap_mim_2f0fF.sym} -400 450 0 0 {name=CB model=cap_mim_2f0fF W=19u L=19u m=1}
C {lab_pin.sym} -400 420 0 0 {name=l_CB_G lab=BLR}
C {lab_pin.sym} -400 480 0 0 {name=l_CB_B lab=VSS}
C {nfet_03v3.sym} -100 450 0 0 {name=IB1N model=nfet_03v3 W=2u L=0.35u nf=1 m=1}
C {lab_pin.sym} -80 420 0 0 {name=l_IB1N_D lab=BLN}
C {lab_pin.sym} -120 450 0 0 {name=l_IB1N_G lab=BLR}
C {lab_pin.sym} -80 480 0 0 {name=l_IB1N_S lab=VSS}
C {lab_pin.sym} -80 450 0 0 {name=l_IB1N_B lab=VSS}
C {pfet_03v3.sym} 200 450 0 0 {name=IB1P model=pfet_03v3 W=4u L=0.35u nf=1 m=1}
C {lab_pin.sym} 220 480 0 0 {name=l_IB1P_D lab=BLN}
C {lab_pin.sym} 180 450 0 0 {name=l_IB1P_G lab=BLR}
C {lab_pin.sym} 220 420 0 0 {name=l_IB1P_S lab=VDD33}
C {lab_pin.sym} 220 450 0 0 {name=l_IB1P_B lab=VDD33}
C {nfet_03v3.sym} 500 450 0 0 {name=IB2N model=nfet_03v3 W=2u L=0.35u nf=1 m=1}
C {lab_pin.sym} 520 420 0 0 {name=l_IB2N_D lab=BLD}
C {lab_pin.sym} 480 450 0 0 {name=l_IB2N_G lab=BLN}
C {lab_pin.sym} 520 480 0 0 {name=l_IB2N_S lab=VSS}
C {lab_pin.sym} 520 450 0 0 {name=l_IB2N_B lab=VSS}
C {pfet_03v3.sym} 800 450 0 0 {name=IB2P model=pfet_03v3 W=4u L=0.35u nf=1 m=1}
C {lab_pin.sym} 820 480 0 0 {name=l_IB2P_D lab=BLD}
C {lab_pin.sym} 780 450 0 0 {name=l_IB2P_G lab=BLN}
C {lab_pin.sym} 820 420 0 0 {name=l_IB2P_S lab=VDD33}
C {lab_pin.sym} 820 450 0 0 {name=l_IB2P_B lab=VDD33}
C {nfet_03v3.sym} 1100 450 0 0 {name=NGNA model=nfet_03v3 W=6u L=0.35u nf=1 m=1}
C {lab_pin.sym} 1120 420 0 0 {name=l_NGNA_D lab=TRN}
C {lab_pin.sym} 1080 450 0 0 {name=l_NGNA_G lab=RAW}
C {lab_pin.sym} 1120 480 0 0 {name=l_NGNA_S lab=NG_n1}
C {lab_pin.sym} 1120 450 0 0 {name=l_NGNA_B lab=VSS}
C {nfet_03v3.sym} 1400 450 0 0 {name=NGNB model=nfet_03v3 W=6u L=0.35u nf=1 m=1}
C {lab_pin.sym} 1420 420 0 0 {name=l_NGNB_D lab=NG_n1}
C {lab_pin.sym} 1380 450 0 0 {name=l_NGNB_G lab=HS_ON}
C {lab_pin.sym} 1420 480 0 0 {name=l_NGNB_S lab=NG_n2}
C {lab_pin.sym} 1420 450 0 0 {name=l_NGNB_B lab=VSS}
C {nfet_03v3.sym} 1700 450 0 0 {name=NGNC model=nfet_03v3 W=6u L=0.35u nf=1 m=1}
C {lab_pin.sym} 1720 420 0 0 {name=l_NGNC_D lab=NG_n2}
C {lab_pin.sym} 1680 450 0 0 {name=l_NGNC_G lab=BLD}
C {lab_pin.sym} 1720 480 0 0 {name=l_NGNC_S lab=VSS}
C {lab_pin.sym} 1720 450 0 0 {name=l_NGNC_B lab=VSS}
C {pfet_03v3.sym} -400 700 0 0 {name=NGPA model=pfet_03v3 W=4u L=0.35u nf=1 m=1}
C {lab_pin.sym} -380 730 0 0 {name=l_NGPA_D lab=TRN}
C {lab_pin.sym} -420 700 0 0 {name=l_NGPA_G lab=RAW}
C {lab_pin.sym} -380 670 0 0 {name=l_NGPA_S lab=VDD33}
C {lab_pin.sym} -380 700 0 0 {name=l_NGPA_B lab=VDD33}
C {pfet_03v3.sym} -100 700 0 0 {name=NGPB model=pfet_03v3 W=4u L=0.35u nf=1 m=1}
C {lab_pin.sym} -80 730 0 0 {name=l_NGPB_D lab=TRN}
C {lab_pin.sym} -120 700 0 0 {name=l_NGPB_G lab=HS_ON}
C {lab_pin.sym} -80 670 0 0 {name=l_NGPB_S lab=VDD33}
C {lab_pin.sym} -80 700 0 0 {name=l_NGPB_B lab=VDD33}
C {pfet_03v3.sym} 200 700 0 0 {name=NGPC model=pfet_03v3 W=4u L=0.35u nf=1 m=1}
C {lab_pin.sym} 220 730 0 0 {name=l_NGPC_D lab=TRN}
C {lab_pin.sym} 180 700 0 0 {name=l_NGPC_G lab=BLD}
C {lab_pin.sym} 220 670 0 0 {name=l_NGPC_S lab=VDD33}
C {lab_pin.sym} 220 700 0 0 {name=l_NGPC_B lab=VDD33}
C {nfet_03v3.sym} 500 700 0 0 {name=ITN model=nfet_03v3 W=4u L=0.35u nf=1 m=1}
C {lab_pin.sym} 520 670 0 0 {name=l_ITN_D lab=TRIP}
C {lab_pin.sym} 480 700 0 0 {name=l_ITN_G lab=TRN}
C {lab_pin.sym} 520 730 0 0 {name=l_ITN_S lab=VSS}
C {lab_pin.sym} 520 700 0 0 {name=l_ITN_B lab=VSS}
C {pfet_03v3.sym} 800 700 0 0 {name=ITP model=pfet_03v3 W=8u L=0.35u nf=1 m=1}
C {lab_pin.sym} 820 730 0 0 {name=l_ITP_D lab=TRIP}
C {lab_pin.sym} 780 700 0 0 {name=l_ITP_G lab=TRN}
C {lab_pin.sym} 820 670 0 0 {name=l_ITP_S lab=VDD33}
C {lab_pin.sym} 820 700 0 0 {name=l_ITP_B lab=VDD33}
