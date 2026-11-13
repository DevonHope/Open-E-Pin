"""Open E-Pin v0.1: the single source of truth for parts and connections.

gen_schematic.py draws the KiCad schematic from this file, and gen_board.py
places the footprints and gives every pad its net from this file. Edit here,
then re-run both scripts so the schematic and board stay in step.

Lines marked VERIFY are taken from datasheets that were only partly
available and must be checked before ordering boards.
"""

# --------------------------------------------------------------------------
# Custom symbols for parts not in the KiCad 7 standard library.
# pins: (number, name, side, electrical type). side is L or R.
# --------------------------------------------------------------------------
CUSTOM_SYMBOLS = {
    "BQ25101": dict(
        ref="U", desc="TI BQ25101 single-cell Li-ion charger, DSBGA-6 (YFP)",
        pins=[("A2", "IN", "L", "power_in"), ("B2", "ISET", "L", "passive"),
              ("B1", "TS", "L", "passive"), ("C2", "VSS", "L", "power_in"),
              ("A1", "OUT", "R", "power_out"), ("C1", "~{CHG}", "R", "open_collector")]),
    "TPS7A0230": dict(
        ref="U", desc="TI TPS7A02 3.0 V 200 mA nano-Iq LDO, SOT-23-5 (DBV). VERIFY pinout",
        pins=[("1", "IN", "L", "power_in"), ("3", "EN", "L", "input"),
              ("2", "GND", "L", "power_in"), ("5", "OUT", "R", "power_out"),
              ("4", "NC", "R", "no_connect")]),
    "TPS22916C": dict(
        ref="U", desc="TI TPS22916C 2 A load switch with output discharge, DSBGA-4 (YFP). VERIFY pinout",
        pins=[("A2", "VIN", "L", "power_in"), ("B2", "ON", "L", "input"),
              ("B1", "GND", "L", "power_in"), ("A1", "VOUT", "R", "power_out")]),
    # Good Display GDEH0169E02 (IST7601 / JD7601 controller), pinout from section 6 of
    # the GDEH0169E02 specification (Good Display, 2026).
    "GDEH0169E02_FPC": dict(
        ref="J", desc="FPC connector for Good Display GDEH0169E02 1.69in round e-paper (32 pin, 0.5 mm pitch)",
        pins=[(str(n), name, "L" if n <= 16 else "R", t) for n, name, t in [
            (1, "VREFR", "passive"), (2, "GDR", "output"), (3, "RESE", "passive"),
            (4, "VDDL", "passive"), (5, "VSH2", "passive"), (6, "VREFL", "passive"),
            (7, "AVDDN", "no_connect"), (8, "BS0", "input"), (9, "BUSY", "output"),
            (10, "RST_N", "input"), (11, "DC", "input"), (12, "CSB", "input"),
            (13, "SCL", "input"), (14, "SDA", "bidirectional"), (15, "VDD", "power_in"),
            (16, "VSH3", "passive"), (17, "GND", "power_in"), (18, "VSL2", "passive"),
            (19, "VSL3", "passive"), (20, "VSH1", "passive"), (21, "VGH", "passive"),
            (22, "VSL1", "passive"), (23, "VGL", "passive"), (24, "VCOM", "passive"),
            (25, "C24M", "no_connect"), (26, "C24P", "no_connect"), (27, "C23M", "no_connect"),
            (28, "C23P", "no_connect"), (29, "C22M", "no_connect"), (30, "C22P", "no_connect"),
            (31, "C21M", "no_connect"), (32, "C21P", "no_connect")]]
        + [("MP", "MP", "R", "passive")]),
}

# --------------------------------------------------------------------------
# Parts: ref -> (symbol, footprint, value, part number / note, block)
# symbol is "Lib:Name" from the KiCad 7 library, or "OpenEPin:Name" for the
# custom symbols above. block groups parts on the schematic sheet.
# --------------------------------------------------------------------------
PARTS = {
    # USB-C input and protection
    "J1": ("Connector:USB_C_Receptacle_USB2.0_14P", "Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal", "USB-C", "GCT USB4105-GF-A", "usb"),
    "F1": ("Device:Polyfuse", "Fuse:Fuse_0603_1608Metric", "0.1A hold", "Bourns MF-PSMF010X-2", "usb"),
    "U5": ("Power_Protection:USBLC6-2P6", "Package_TO_SOT_SMD:SOT-23-6", "USBLC6-2SC6", "ST USBLC6-2SC6", "usb"),
    "R6": ("Device:R", "Resistor_SMD:R_0402_1005Metric", "5.1k", "1%", "usb"),
    "R7": ("Device:R", "Resistor_SMD:R_0402_1005Metric", "5.1k", "1%", "usb"),
    # Charger
    "U2": ("OpenEPin:BQ25101", "OpenEPin:Texas_YFP0006_DSBGA-6_0.9x1.6mm_P0.4mm", "BQ25101", "TI BQ25101YFPR (YFP0006, 0.4 mm pitch)", "charge"),
    "C1": ("Device:C", "Capacitor_SMD:C_0402_1005Metric", "1u 25V", "X5R", "charge"),
    "C2": ("Device:C", "Capacitor_SMD:C_0402_1005Metric", "1u 10V", "X5R", "charge"),
    "R1": ("Device:R", "Resistor_SMD:R_0402_1005Metric", "4.53k", "ISET: 135/4530 = 30 mA (use 5.6k for 24 mA cells)", "charge"),
    "TH1": ("Device:Thermistor_NTC", "Resistor_SMD:R_0402_1005Metric", "10k B3380", "Murata NCP15XH103F03RC, touching the cell", "charge"),
    "R11": ("Device:R", "Resistor_SMD:R_0402_1005Metric", "2.2k", "", "charge"),
    "LED1": ("Device:LED", "LED_SMD:LED_0402_1005Metric", "red", "charge indicator", "charge"),
    "R14": ("Device:R", "Resistor_SMD:R_0402_1005Metric", "100k", "limits CHG node current into the 3 V GPIO", "charge"),
    # Battery and reverse-polarity protection
    "J2": ("Connector_Generic_MountingPin:Conn_01x02_MountingPin", "Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal", "BATT JST-PH", "JST S2B-PH-SM4-TB. Pin 1 = +", "battery"),
    "Q1": ("Device:Q_PMOS_GSD", "Package_TO_SOT_SMD:SOT-23", "DMG2305UX", "Diodes DMG2305UX-7", "battery"),
    "Q2": ("Transistor_FET:DMG1012T", "Package_TO_SOT_SMD:SOT-523", "DMG1012T", "Diodes DMG1012T-7", "battery"),
    "R4": ("Device:R", "Resistor_SMD:R_0402_1005Metric", "10M", "Q1 gate pull-up", "battery"),
    "R5": ("Device:R", "Resistor_SMD:R_0402_1005Metric", "100k", "Q2 gate", "battery"),
    "R2": ("Device:R", "Resistor_SMD:R_0402_1005Metric", "10M", "battery divider top, 1%", "battery"),
    "R3": ("Device:R", "Resistor_SMD:R_0402_1005Metric", "10M", "battery divider bottom, 1%", "battery"),
    "C5": ("Device:C", "Capacitor_SMD:C_0402_1005Metric", "100n", "ADC hold", "battery"),
    # 3.0 V rail and MCU
    "U3": ("OpenEPin:TPS7A0230", "Package_TO_SOT_SMD:SOT-23-5", "TPS7A0230", "TI TPS7A0230PDBVR", "mcu"),
    "C3": ("Device:C", "Capacitor_SMD:C_0402_1005Metric", "1u", "", "mcu"),
    "C4": ("Device:C", "Capacitor_SMD:C_0402_1005Metric", "1u", "", "mcu"),
    "C6": ("Device:C", "Capacitor_SMD:C_0402_1005Metric", "4.7u", "module VDD bulk", "mcu"),
    "C7": ("Device:C", "Capacitor_SMD:C_0402_1005Metric", "100n", "module VDD", "mcu"),
    "U1": ("RF_Module:MDBT50Q-1MV2", "RF_Module:Raytac_MDBT50Q", "MDBT50Q-1MV2", "Raytac nRF52840 module, chip antenna", "mcu"),
    "SW1": ("Switch:SW_Push", "Button_Switch_SMD:SW_SPST_EVQP7A", "BUTTON", "Panasonic EVQ-P7A side-press", "mcu"),
    "TP1": ("Connector:TestPoint", "TestPoint:TestPoint_Pad_1.0x1.0mm", "3V0", "SWD", "mcu"),
    "TP2": ("Connector:TestPoint", "TestPoint:TestPoint_Pad_1.0x1.0mm", "SWDIO", "SWD", "mcu"),
    "TP3": ("Connector:TestPoint", "TestPoint:TestPoint_Pad_1.0x1.0mm", "SWDCLK", "SWD", "mcu"),
    "TP4": ("Connector:TestPoint", "TestPoint:TestPoint_Pad_1.0x1.0mm", "RESET", "SWD", "mcu"),
    "TP5": ("Connector:TestPoint", "TestPoint:TestPoint_Pad_1.0x1.0mm", "GND", "SWD", "mcu"),
    # Display power switch, connector and booster, per the GDEH0169E02
    # specification reference circuit (figures 7-1 and 7-2).
    "U4": ("OpenEPin:TPS22916C", "OpenEPin:Texas_YFP0004_DSBGA-4_0.78x0.78mm_P0.4mm", "TPS22916C", "TI TPS22916CYFPR (YFP0004, 0.4 mm pitch)", "display"),
    "J3": ("OpenEPin:GDEH0169E02_FPC", "Connector_FFC-FPC:Hirose_FH12-32S-0.5SH_1x32-1MP_P0.50mm_Horizontal", "GDEH0169E02", "Hirose FH12-32S-0.5SH. VERIFY contact side: panel FPC contacts face the board after the fold", "display"),
    "L1": ("Device:L", "Inductor_SMD:L_Taiyo-Yuden_NR-30xx", "47uH", "Taiyo Yuden NRH3010T470MN", "display"),
    "Q3": ("Device:Q_NMOS_GSD", "Package_TO_SOT_SMD:SOT-23", "NX3008NBK", "Nexperia NX3008NBK or Vishay Si1304BDL (Vds>=30V, Vgs(th) 1.3V max)", "display"),
    "R8": ("Device:R", "Resistor_SMD:R_0603_1608Metric", "0.47", "1%, booster current sense", "display"),
    "R15": ("Device:R", "Resistor_SMD:R_0402_1005Metric", "10k", "booster FET gate pull-down", "display"),
    "D1": ("Device:D_Schottky", "Diode_SMD:D_SOD-323", "NSR0530H", "VGH diode. 30 V, 0.5 A, Vf<=430 mV (MBR0530 class)", "display"),
    "D2": ("Device:D_Schottky", "Diode_SMD:D_SOD-323", "NSR0530H", "charge pump to GND. 30 V, 0.5 A, Vf<=430 mV", "display"),
    "D3": ("Device:D_Schottky", "Diode_SMD:D_SOD-323", "NSR0530H", "VGL diode. 30 V, 0.5 A, Vf<=430 mV", "display"),
    "R12": ("Device:R", "Resistor_SMD:R_0402_1005Metric", "10k", "BS0 low = 4-wire SPI", "display"),
    "C10": ("Device:C", "Capacitor_SMD:C_0402_1005Metric", "1u 25V", "EPD_VDD (VCCI) 1u, X5R", "display"),
    "C11": ("Device:C", "Capacitor_SMD:C_0402_1005Metric", "1u 25V", "VGH, X5R", "display"),
    "C12": ("Device:C", "Capacitor_SMD:C_0402_1005Metric", "1u 25V", "VGL, X5R", "display"),
    "C13": ("Device:C", "Capacitor_SMD:C_0402_1005Metric", "1u 25V", "pin 1 VREFR, X5R", "display"),
    "C14": ("Device:C", "Capacitor_SMD:C_0402_1005Metric", "1u 25V", "pin 4 VDDL, X5R", "display"),
    "C15": ("Device:C", "Capacitor_SMD:C_0402_1005Metric", "1u 25V", "pin 5 VSH2, X5R", "display"),
    "C16": ("Device:C", "Capacitor_SMD:C_0402_1005Metric", "1u 25V", "pin 6 VREFL, X5R", "display"),
    "C17": ("Device:C", "Capacitor_SMD:C_0402_1005Metric", "1u 25V", "pin 15 VDD, X5R", "display"),
    "C18": ("Device:C", "Capacitor_SMD:C_0402_1005Metric", "1u 25V", "pin 16 VSH3, X5R", "display"),
    "C19": ("Device:C", "Capacitor_SMD:C_0402_1005Metric", "1u 25V", "pin 18 VSL2, X5R", "display"),
    "C20": ("Device:C", "Capacitor_SMD:C_0402_1005Metric", "1u 35V", "pin 19 VSL3 (35 V per reference), X5R", "display"),
    "C21": ("Device:C", "Capacitor_SMD:C_0402_1005Metric", "1u 25V", "pin 20 VSH1, X5R", "display"),
    "C22": ("Device:C", "Capacitor_SMD:C_0402_1005Metric", "1u 25V", "pin 22 VSL1, X5R", "display"),
    "C23": ("Device:C", "Capacitor_SMD:C_0402_1005Metric", "1u 25V", "pin 24 VCOM, X5R", "display"),
    "C24": ("Device:C", "Capacitor_SMD:C_0402_1005Metric", "1u 25V", "charge-pump flying cap, X5R", "display"),
}

# --------------------------------------------------------------------------
# Nets: name -> list of "REF.PIN". Pins not listed anywhere get a no-connect.
# --------------------------------------------------------------------------
NETS = {
    "GND": ["J1.A1", "J1.A12", "J1.B1", "J1.B12", "J1.S1", "U5.2", "R6.2", "R7.2",
            "U2.C2", "R1.2", "TH1.2", "J2.2", "J2.MP", "Q2.2", "R3.2", "C5.2",
            "C1.2", "C2.2", "C3.2", "C4.2", "C6.2", "C7.2", "U3.2",
            "U1.1", "U1.2", "U1.15", "U1.33", "U1.55", "SW1.2", "TP5.1",
            "U4.B1", "J3.17", "J3.MP", "R8.2", "R12.2", "R15.2", "D2.1"]
           + [f"C{n}.2" for n in range(10, 24)],
    "VBUS_IN": ["J1.A4", "J1.A9", "J1.B4", "J1.B9", "F1.1"],
    "VBUS": ["F1.2", "U5.5", "U2.A2", "C1.1", "U1.32", "R11.1"],
    "CC1": ["J1.A5", "R6.1"],
    "CC2": ["J1.B5", "R7.1"],
    "USB_D+": ["J1.A6", "J1.B6", "U5.1", "U5.6", "U1.35"],
    "USB_D-": ["J1.A7", "J1.B7", "U5.3", "U5.4", "U1.34"],
    "ISET": ["U2.B2", "R1.1"],
    "TS": ["U2.B1", "TH1.1"],
    "CHG_N": ["U2.C1", "LED1.1", "R14.1"],
    "LED_A": ["R11.2", "LED1.2"],
    "CHG_SENSE": ["R14.2", "U1.12"],                 # P0.31
    "BAT_CONN": ["J2.1", "Q1.3", "R5.1"],
    "Q1_GATE": ["Q1.1", "R4.2", "Q2.3"],
    "Q2_GATE": ["R5.2", "Q2.1"],
    "VBAT_SYS": ["U2.A1", "C2.1", "Q1.2", "R4.1", "R2.1", "U3.1", "U3.3", "C3.1"],
    "VBAT_SENSE": ["R2.2", "R3.1", "C5.1", "U1.10"],  # P0.29 / AIN5
    "3V0": ["U3.5", "C4.1", "C6.1", "C7.1", "U1.28", "U1.30", "U4.A2", "TP1.1"],
    "EPD_PWR_EN": ["U4.B2", "U1.47"],                # P1.00
    "EPD_VDD": ["U4.A1", "J3.15", "C10.1", "C17.1", "L1.1"],   # VCCI in the reference
    "SWDIO": ["U1.51", "TP2.1"],
    "SWDCLK": ["U1.53", "TP3.1"],
    "RESET": ["U1.40", "TP4.1"],                     # P0.18
    "BUTTON": ["SW1.1", "U1.57"],                    # P1.06
    "EPD_BUSY": ["J3.9", "U1.37"],                   # P0.13
    "EPD_RST": ["J3.10", "U1.39"],                   # P0.15
    "EPD_DC": ["J3.11", "U1.41"],                    # P0.17
    "EPD_CS": ["J3.12", "U1.44"],                    # P0.20
    "EPD_SCK": ["J3.13", "U1.46"],                   # P0.22
    "EPD_MOSI": ["J3.14", "U1.48"],                  # P0.24
    "EPD_BS0": ["J3.8", "R12.1"],
    # Booster (figure 7-2): L1 from VCCI to the switch node, Q3 switches it,
    # D1 rectifies VGH, C24 + D2 + D3 make the negative VGL.
    "EPD_GDR": ["J3.2", "Q3.1", "R15.1"],
    "EPD_RESE": ["J3.3", "Q3.2", "R8.1"],
    "EPD_SW": ["L1.2", "Q3.3", "D1.2", "C24.1"],
    "EPD_PUMP": ["C24.2", "D2.2", "D3.1"],
    "EPD_VGH": ["D1.1", "J3.21", "C11.1"],
    "EPD_VGL": ["D3.2", "J3.23", "C12.1"],
    # Rail capacitors (figure 7-1), each 1 uF to GND.
    "EPD_VREFR": ["J3.1", "C13.1"],
    "EPD_VDDL": ["J3.4", "C14.1"],
    "EPD_VSH2": ["J3.5", "C15.1"],
    "EPD_VREFL": ["J3.6", "C16.1"],
    "EPD_VSH3": ["J3.16", "C18.1"],
    "EPD_VSL2": ["J3.18", "C19.1"],
    "EPD_VSL3": ["J3.19", "C20.1"],
    "EPD_VSH1": ["J3.20", "C21.1"],
    "EPD_VSL1": ["J3.22", "C22.1"],
    "EPD_VCOM": ["J3.24", "C23.1"],
}

BLOCK_TITLES = {
    "usb": "USB-C input: PTC fuse, ESD, CC pull-downs",
    "charge": "Charger: BQ25101 at 30 mA, NTC at the cell, charge LED",
    "battery": "Battery: JST-PH, reverse-polarity FETs, voltage sense",
    "mcu": "3.0 V LDO, nRF52840 module, button, SWD pads",
    "display": "Display GDEH0169E02: power switch, 32-pin FPC, VGH/VGL booster and rail caps (spec figures 7-1, 7-2)",
}


def check():
    """Every net pin must name a real part, and no pin may be in two nets."""
    seen = {}
    for net, pins in NETS.items():
        for p in pins:
            ref, pin = p.split(".", 1)
            assert ref in PARTS, f"{p} in {net}: unknown part"
            assert p not in seen, f"{p} is in both {seen[p]} and {net}"
            seen[p] = net
    return seen


if __name__ == "__main__":
    s = check()
    print(f"{len(PARTS)} parts, {len(NETS)} nets, {len(s)} connected pins")
