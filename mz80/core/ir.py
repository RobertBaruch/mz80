from nmigen import *

from .muxing import *


class IR(Elaboratable):
    def __init__(self):
        self.controls = SequencerControls()

        self.I = Signal(8)
        self.R = Signal(7)
        self.dataBusIn = Signal(8)
        self.dataBusOut = Signal(8)
        self.addrBusOut = Signal(16)

    def elaborate(self, platform):
        m = Module()

        with m.If(self.controls.readRegister8 == Register8.I):
            m.d.comb += self.dataBusOut.eq(self.I)
        with m.Elif(self.controls.readRegister8 == Register8.R):
            m.d.comb += self.dataBusOut.eq(self.R)
        with m.Else():
            m.d.comb += self.dataBusOut.eq(0)

        with m.If(self.controls.readRegister16 == Register16.R):
            m.d.comb += self.addrBusOut.eq(self.R)
        with m.Else():
            m.d.comb += self.addrBusOut.eq(0)

        with m.If(self.controls.writeRegister8 == Register8.I):
            m.d.pos += self.I.eq(self.dataBusIn)
        with m.Elif(self.controls.writeRegister8 == Register8.R):
            m.d.pos += self.R.eq(self.dataBusIn)
        with m.Elif(self.controls.incR == 1):
            m.d.pos += self.R.eq(self.R + 1)

        return m