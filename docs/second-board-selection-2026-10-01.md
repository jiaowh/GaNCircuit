# Second-board selection for diagnosing the EPC90133 mismatch

Search date: 1 October 2026 (Asia/Singapore). Recommendation, not a purchase or
replacement of the active EPC90133 baseline.

## Pick: EPC9165KIT for a comparative measurement experiment

EPC9165 preserves EPC2302 in both switch positions and uses an MPQ1918 driver.
Its published schematic shows 1 ohm turn-on and 0 ohm turn-off gate resistors.
This makes it a useful test of whether the EPC90133 discrepancy transfers to
the same transistor type with different drive circuitry and board construction.
Driver and layout change together; this is not an isolated driver substitution.
Sources: [schematic](https://epc-co.com/epc/Portals/0/epc/documents/schematics/EPC9165_Schematic.pdf),
[EPC application-board selector](https://epc-co.com/epc/products/evaluation-boards/application-specific-evaluation-boards).

The kit includes EPC9165 and EPC9528. EPC describes a two-phase 48 V/14 V converter,
500 kHz operation, and a one-phase configuration option. Its page lists schematic,
BOM and Gerbers; editable Altium files require a request. Only the guide and schematic
were downloaded in this screening; Gerber/BOM content and matching revisions remain
unchecked. [Product page](https://epc-co.com/epc/products/evaluation-boards/epc9165).

The public guide includes buck/boost switch-node captures (Fig. 11), but does not
declare their switched current or probe chain. Its explicit test-point list addresses
rail measurements and control-loop injection rather than a characterized gate/SW
probe interface. A heatsink is supplied over the FET region. Consequently, convenient
high-bandwidth gate access is not established by this screening. Probe access and
actual board revision/population are prerequisites to a purchase decision for this
experiment. [Guide](https://epc-co.com/epc/Portals/0/epc/documents/guides/EPC9165_qsg.pdf).

The DigiKey US listing inspected shows USD 812.50 and stock; this is an indicative
listing, not a Singapore quote or reserved availability.
[Listing](https://www.digikey.com/en/products/detail/epc/EPC9165KIT/15930010).

## Important simulation limitation

An MPS FAE stated on 8 September 2026 that MPQ1918 has no official PSpice or MPSmart
model and that MPS has no official LTspice models to their knowledge.
[MPS response](https://forum.monolithicpower.com/t/mpq1918-pspice-simulation-model/6349).

Do not introduce another unconstrained driver approximation and treat its agreement
as validation. This board's value is highest when its driver waveform can be measured.
The EPC2302 vendor model can be reused unchanged, but its qualification exceptions
remain; the new driver, layout, supplies and operating conditions require their own
records. No claim is made that an EPC9165 model already runs in our adapter.

## Alternatives screened

| Board | Diagnostic value and reason not selected first |
|---|---|
| EPC90142 | Same EPC2302 only on the low side; EPC23101 integrates a different high-side FET and drive. Changes the very high-side device whose channel dominates our deviation metric. EPC currently marks EPC23101 obsolete. |
| EPC9097 | Same uP1966E family, different EPC2204 device; substantial existing project tooling makes this the cheapest additional software case. It tests transfer across devices, not the same-device driver question. The recorded layout/population ambiguity still needs resolution. |
| EPC90156 | Same uP1966E, different EPC2361; new device qualification needed without preserving EPC2302. |
| EPC9194 | Same EPC2302 with STDRIVEG600; a credible alternative if physical probe access is better. Motor-oriented three-phase system with deliberately slower stock switching adds setup and excitation differences. |
| EPC9186 | Four EPC2302s in parallel per switch position; unnecessary current-sharing and coupling variables for the first comparison. |

Sources: [EPC90142](https://epc-co.com/epc/products/evaluation-boards/epc90142),
[EPC23101 status](https://epc-co.com/epc/products/gan-fets-and-ics/epc23101),
[EPC9097](https://epc-co.com/epc/products/evaluation-boards/epc9097),
[EPC90156](https://epc-co.com/epc/products/evaluation-boards/epc90156),
[EPC9194](https://epc-co.com/epc/products/evaluation-boards/epc9194),
[driver selector](https://epc-co.com/epc/products/evaluation-boards/application-specific-evaluation-boards),
[EPC9186 announcement](https://epc-co.com/epc/design-support/technical-publications/articles/artmid/9702/articleid/3123/150-arms-motor-drive-reference-design-with-gan-fets-provides-best-performance-for-emobility-forklifts-and-high-power-drones).

## What the experiment would answer

Declare an overlapping operating subset after inventory and setup review. Match bus
voltage, current at the actual commutation edge, temperature and measurement response;
record gate waveforms, dead time, supply behavior and periodic-operation differences.
Do not equate total two-phase output current with a single edge's FET current.
Resolve how the second phase is operated or disabled through a reviewed controller
configuration; the product's one-phase statement is not an executable procedure.

Build a separate board prediction from its own geometry and measured driver inputs.
Freeze it before inspecting held-out switching measurements. Compare model-minus-
measurement residuals on both boards, not just their raw overshoots:

- A similar residual across both strengthens shared-model/measurement explanations,
  without uniquely identifying a device error.
- A large residual only on EPC90133 strengthens board-specific drive/layout/setup
  explanations, without separating them automatically.
- Correctly predicted differences despite common absolute error support transfer of
  relative predictions over the tested conditions.

If only published waveforms and simulation are currently available, EPC9165 Fig. 11
is qualitative corroboration, not a pass/fail validation target with matched current.
EPC9097 is the lower-effort additional simulation case already present in the project.

## Retrieval and inspection record

Two downloaded PDFs are pinned in
`devices/epc/second-board-screening-sources-2026-10-01.json`; originals and page previews
remain in git-ignored `vendor/epc/second-board-screening/`. Visually inspected schematic
pages 4/5 and guide pages 4/9 using PyMuPDF rendering. Public support links are not proof
of unrestricted reuse or of KiCad importability. No EPC inquiry was sent, no hardware
was ordered, no extraction or circuit simulation was launched, and the active target
was not changed.

## File audit and probe access (added 1 October 2026)

Done after the owner's decision to defer the purchase (plan section 9, item 10); details in docs/build.md,
"EPC9165 board files and probe access". The published Gerbers are B5309 Rev 1.0, while the guide's schematic is
B5284 Rev 1.0, so the shipped board's identity is open. The EPC2302s and their gate resistors are on the bottom
under the heatsink and there is no gate-probe footprint: gate measurements need the heatsink removed, so a matched
comparison would be double pulse. The switch node is reachable on the top side 1.1-2.2 mm from the FETs with a
solder-in probe. The two 100 mil headers (J1_F1/F2) are loop-gain injection points, not switch-node test points.
