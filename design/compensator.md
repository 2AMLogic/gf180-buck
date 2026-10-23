# Type-III compensator and modulator: derivation and design-to values

Spec row R13 (`spec/target-spec.md`): voltage-mode PWM, type-III compensation,
PM >= 45 deg, GM >= 10 dB, fc 100-250 kHz (target tier, P-T parts, 2 MHz).
These values are **design-to**: ideal op-amp and ideal R/C. Nothing here is
measured. Values the spec does not fix (Vramp, Vref, the divider, every R and
C below) are first stated in this file.

## Plant (averaged, CCM, forced PWM per R6)

`Vsw = d * Vin`, `d = Vc / Vramp` (fixed ramp, no Vin feed-forward). With the
ideal current-sink load of spec section 0.2 the small-signal load impedance is
infinite, so

    Gvd(s) = Vin * Zc / (Zc + Zs)
    Zc = ESR + s*ESL + 1/(s*Ceff)
    Zs = (Rpk + s*Lpk) + [(DCR + s*L) || 1/(s*Cw)]

DC loop gain is `Vin/Vramp` times the compensator; below the LC double pole
`f0 = 1/(2*pi*sqrt(L*Ceff))` (35.8 kHz nominal) the plant is flat, above it
falls at -2. The ESR zero `1/(2*pi*ESR*Ceff)` is 1.3-6.8 MHz over the P-T
tolerance box, i.e. above the switching half-frequency, so it adds no phase
at crossover and is not cancelled. Load current changes only the operating
point (duty), not `Gvd`, because the switch is ideal and the load a current
sink; the sweep records this rather than assuming it.

Parts: L 3.3 uH +/-20 %, DCR 100 mOhm (typ), Cw 3 pF, Ceff 4.7 / 6 / 12 uF,
ESR 5 / 10 mOhm, ESL 0.5 nH (P-T, section 0.2). SW net: 2 wires in parallel,
typ 0.10 ohm / 2.0 nH each, so Rpk = 50 mOhm, Lpk = 1 nH in series with L
(section 0.3). The VIN and GND wires are not in the plant (see Assumptions).

## Compensator (Venable type III, inverting, ideal op-amp)

    Zi = Rtop || (R3 + 1/(s*C3))        Zf = (R2 + 1/(s*C1)) || 1/(s*C2)
    Gc = Zf/Zi = (1 + s*R2*C1)(1 + s*(Rtop+R3)*C3)
                 / [ s*Rtop*(C1+C2) (1 + s*R2*C1*C2/(C1+C2)) (1 + s*R3*C3) ]

    fz1 = 1/(2*pi*R2*C1)          fz2 = 1/(2*pi*(Rtop+R3)*C3)
    fp1 = 1/(2*pi*R3*C3)          fp2 = 1/(2*pi*R2*C1*C2/(C1+C2))

Placement:

- **Reference and divider.** Vout = 1.8 V, Vref = 0.6 V, so Rtop/Rbot = 2.
  Rtop = 10 kOhm, Rbot = 5 kOhm. Rbot is DC bias only; the op-amp input is a
  virtual ground at AC.
- **Two zeros at fz1 = fz2 = 20 kHz**, below the lowest `f0` in the tolerance
  box (23 kHz at L +20 %, Ceff 12 uF) so the phase boost is already in place
  before the double pole.
- **Two poles at fp1 = fp2 = 1 MHz = fsw/2.** The ESR zero (>= 1.3 MHz) is not
  a usable cancellation target; the poles instead set the switching-ripple
  rejection and the gain-margin frequency.
- **Crossover target 150 kHz at nominal** (Vin 5 V, L 3.3 uH, Ceff 6 uF,
  ESR 5 mOhm), set by scaling C1 (R2 follows from fz1) until |T(150 kHz)| = 1.

Closed-form steps (Rtop = 10 kOhm):

    R3  = Rtop / (fp1/fz2 - 1) = 10 k / 49          = 204 ohm
    C3  = 1 / (2*pi*R3*fp1)                          = 780 pF
    C2  = C1 / (fp2/fz1 - 1) = C1 / 49
    R2  = 1 / (2*pi*fz1*C1)
    C1  : bisected so |T(2*pi*150 kHz)| = 1          -> 1.75 nF

### Design-to values (rounded to 3 significant figures; these are what the deck uses)

| Quantity | Value |
|---|---|
| Vramp (peak-to-peak, fixed) | 1.0 V |
| Vref | 0.6 V |
| Rtop / Rbot | 10 kOhm / 5 kOhm |
| R2 | 4.55 kOhm |
| R3 | 204 ohm |
| C1 | 1.75 nF |
| C2 | 35.7 pF |
| C3 | 780 pF |
| fz1, fz2 (nominal, after rounding) | 20.0 kHz, 20.0 kHz |
| fp1, fp2 | 1.00 MHz, 1.00 MHz |

C2 = 35.7 pF is small enough that layout parasitics would matter in a real
build; this is an ideal-part design-to value, not a BOM.

## Loop break

Middlebrook series voltage injection: `Vinj` (DC 0, AC 1) sits between Vout
(node `vo`) and the compensator input (node `b`), `b = vo + vinj`. The source
impedance at `vo` (an LC output, tens of milliohms at crossover) is far below
`Rtop` (10 kOhm), the condition for a valid voltage injection. With negative
feedback `vo = -T * b`, so `T = -v(vo)/v(b)`; DC stays closed, so the
operating point (including the duty cycle for each load) is the real one.

## Assumptions (every number from this bench carries these)

- Ideal op-amp: flat open-loop gain 1e6, no GBW. The finite GBW of the adopted
  `error_amplifier` (`reuse.lock.json`) is **not** included.
- Ideal averaged switch: no Ron, no dead time, no gate-drive or comparator
  delay. PDK-free by construction.
- Ideal current-sink load (section 0.2).
- Inductor DCR at its typ 100 mOhm, not the 150 mOhm max; less damping is the
  conservative side for phase margin. DCR is not a swept axis.
- VIN and GND package wires are not in the plant (they carry current for
  `d` and `1-d` of the cycle and add a few mOhm of duty-dependent damping).
- Fixed ramp, no Vin feed-forward, so Vin enters the loop gain directly.
- An analytic expectation, stated here so the sweep can confirm or refute it:
  well above `f0` the loop gain scales as `Vin/(L*Ceff)` at slope -1, so fc
  moves by about 3.8x (L x Ceff) times 1.2x (Vin) across the tolerance box,
  against a 2.5x band (100-250 kHz). A fixed linear compensator cannot hold
  every point inside the band; any point outside is reported as a failure,
  not retuned. The spec is not relaxed here.
