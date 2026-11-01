v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {buck_top: gf180-buck top level -- power stage + gate drive + controller + compensator (issue #35)} -600 -900 0 0 0.5 0.5 {}
T {Joins the blocks of #33 (power_stage, gate_drive), #34 (osc_ramp, pwm_comp, soft_start, ocp_sense) and the compensator.} -600 -850 0 0 0.3 0.3 {}
T {L and Cout are external: SW leaves the die, the LC filter returns on VOUT (sense input).  Bias generator, bandgap (VBG) and the} -600 -820 0 0 0.3 0.3 {}
T {3.3 V regulator (VDD33) are not in this design's blocks yet: they are top-level ports.  All grounds are GND (blocks' VSS -> GND).} -600 -790 0 0 0.3 0.3 {}
T {Integration choices: HS_ON = PWM (the high-side command; ocp_sense blanks ~50 ns).  VREF_SS -> compensator VREF as documented,} -600 -760 0 0 0.3 0.3 {}
T {but soft_start ends at VBG = 1.2 V and the design-to Vref is 0.6 V: recorded open in design/README.md, not resolved here.} -600 -730 0 0 0.3 0.3 {}
C {iopin.sym} -900 -800 0 0 {name=p_VIN lab=VIN}
C {iopin.sym} -900 -760 0 0 {name=p_VDD33 lab=VDD33}
C {iopin.sym} -900 -720 0 0 {name=p_GND lab=GND}
C {iopin.sym} -900 -680 0 0 {name=p_SW lab=SW}
C {ipin.sym} -900 -640 0 0 {name=p_VOUT lab=VOUT}
C {ipin.sym} -900 -600 0 0 {name=p_EN lab=EN}
C {ipin.sym} -900 -560 0 0 {name=p_VBG lab=VBG}
C {ipin.sym} -900 -520 0 0 {name=p_IBIAS_OSC lab=IBIAS_OSC}
C {ipin.sym} -900 -480 0 0 {name=p_IBIAS_PWM lab=IBIAS_PWM}
C {ipin.sym} -900 -440 0 0 {name=p_IBIAS_SS lab=IBIAS_SS}
C {ipin.sym} -900 -400 0 0 {name=p_IBIAS_OCP lab=IBIAS_OCP}
C {ipin.sym} -900 -360 0 0 {name=p_IBIAS_EA lab=IBIAS_EA}
C {ipin.sym} -900 -320 0 0 {name=p_TRIM0 lab=TRIM0}
C {ipin.sym} -900 -280 0 0 {name=p_TRIM1 lab=TRIM1}
C {ipin.sym} -900 -240 0 0 {name=p_TRIM2 lab=TRIM2}
C {opin.sym} -900 -200 0 0 {name=p_VC lab=VC}
C {opin.sym} -900 -160 0 0 {name=p_PWM lab=PWM}
C {opin.sym} -900 -120 0 0 {name=p_VREF_SS lab=VREF_SS}
C {osc_ramp.sym} -400 -300 0 0 {name=XOSC}
C {lab_pin.sym} -480 -400 0 0 {name=l_XOSC_IBIAS lab=IBIAS_OSC}
C {lab_pin.sym} -480 -360 0 0 {name=l_XOSC_TRIM0 lab=TRIM0}
C {lab_pin.sym} -480 -320 0 0 {name=l_XOSC_TRIM1 lab=TRIM1}
C {lab_pin.sym} -480 -280 0 0 {name=l_XOSC_TRIM2 lab=TRIM2}
C {lab_pin.sym} -480 -240 0 0 {name=l_XOSC_VDD33 lab=VDD33}
C {lab_pin.sym} -480 -200 0 0 {name=l_XOSC_VSS lab=GND}
C {lab_pin.sym} -320 -400 0 0 {name=l_XOSC_CLK lab=CLK}
C {lab_pin.sym} -320 -360 0 0 {name=l_XOSC_RAMP lab=RAMP}
C {pwm_comp.sym} 200 -300 0 0 {name=XPWM}
C {lab_pin.sym} 120 -400 0 0 {name=l_XPWM_VC lab=VC}
C {lab_pin.sym} 120 -360 0 0 {name=l_XPWM_RAMP lab=RAMP}
C {lab_pin.sym} 120 -320 0 0 {name=l_XPWM_CLK lab=CLK}
C {lab_pin.sym} 120 -280 0 0 {name=l_XPWM_OCP_TRIP lab=TRIP}
C {lab_pin.sym} 120 -240 0 0 {name=l_XPWM_IBIAS lab=IBIAS_PWM}
C {lab_pin.sym} 120 -200 0 0 {name=l_XPWM_VDD33 lab=VDD33}
C {lab_pin.sym} 120 -160 0 0 {name=l_XPWM_VSS lab=GND}
C {lab_pin.sym} 280 -400 0 0 {name=l_XPWM_PWM lab=PWM}
C {soft_start.sym} 800 -300 0 0 {name=XSS}
C {lab_pin.sym} 720 -400 0 0 {name=l_XSS_IBIAS lab=IBIAS_SS}
C {lab_pin.sym} 720 -360 0 0 {name=l_XSS_VBG lab=VBG}
C {lab_pin.sym} 720 -320 0 0 {name=l_XSS_EN lab=EN}
C {lab_pin.sym} 720 -280 0 0 {name=l_XSS_VDD33 lab=VDD33}
C {lab_pin.sym} 720 -240 0 0 {name=l_XSS_VSS lab=GND}
C {lab_pin.sym} 880 -400 0 0 {name=l_XSS_VREF_SS lab=VREF_SS}
C {lab_pin.sym} 880 -360 0 0 {name=l_XSS_CSS lab=CSS}
C {ocp_sense.sym} -400 200 0 0 {name=XOCP}
C {lab_pin.sym} -480 100 0 0 {name=l_XOCP_SW lab=SW}
C {lab_pin.sym} -480 140 0 0 {name=l_XOCP_HS_ON lab=PWM}
C {lab_pin.sym} -480 180 0 0 {name=l_XOCP_IBIAS lab=IBIAS_OCP}
C {lab_pin.sym} -480 220 0 0 {name=l_XOCP_VIN lab=VIN}
C {lab_pin.sym} -480 260 0 0 {name=l_XOCP_VDD33 lab=VDD33}
C {lab_pin.sym} -480 300 0 0 {name=l_XOCP_VSS lab=GND}
C {lab_pin.sym} -320 100 0 0 {name=l_XOCP_TRIP lab=TRIP}
C {compensator.sym} 200 200 0 0 {name=XCOMP}
C {lab_pin.sym} 120 100 0 0 {name=l_XCOMP_VOUT lab=VOUT}
C {lab_pin.sym} 120 140 0 0 {name=l_XCOMP_VREF lab=VREF_SS}
C {lab_pin.sym} 120 180 0 0 {name=l_XCOMP_IBIAS lab=IBIAS_EA}
C {lab_pin.sym} 120 220 0 0 {name=l_XCOMP_VDD33 lab=VDD33}
C {lab_pin.sym} 120 260 0 0 {name=l_XCOMP_GND lab=GND}
C {lab_pin.sym} 280 100 0 0 {name=l_XCOMP_VC lab=VC}
C {gate_drive.sym} 800 200 0 0 {name=XGD}
C {lab_pin.sym} 720 100 0 0 {name=l_XGD_PWM lab=PWM}
C {lab_pin.sym} 720 140 0 0 {name=l_XGD_VDD3 lab=VDD33}
C {lab_pin.sym} 720 180 0 0 {name=l_XGD_VIN lab=VIN}
C {lab_pin.sym} 720 220 0 0 {name=l_XGD_GND lab=GND}
C {lab_pin.sym} 880 100 0 0 {name=l_XGD_GH lab=GH}
C {lab_pin.sym} 880 140 0 0 {name=l_XGD_GL lab=GL}
C {power_stage.sym} -400 700 0 0 {name=XPS}
C {lab_pin.sym} -480 600 0 0 {name=l_XPS_GH lab=GH}
C {lab_pin.sym} -480 640 0 0 {name=l_XPS_GL lab=GL}
C {lab_pin.sym} -480 680 0 0 {name=l_XPS_VIN lab=VIN}
C {lab_pin.sym} -480 720 0 0 {name=l_XPS_SW lab=SW}
C {lab_pin.sym} -480 760 0 0 {name=l_XPS_GND lab=GND}
