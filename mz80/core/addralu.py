from nmigen import *
from nmigen.cli import main
from nmigen.asserts import *

from .muxing import *


class AddrALU(Elaboratable):
    """An 8-bit ALU that only adds and has a carry.

    A 16-bit add is carried out by first loading the offset register.
    Then, reading the result (reading ADDR_ALU) yields the low byte,
    and saves the carry on the next positive clock. Then the offset
    becomes FF or 00 depending on the sign of offset, and the high byte
    is added.

    When ADDR_ALU is no longer being read, carry is reset to 0.
    """

    def __init__(self):
        self.controls = SequencerControls()

        self.input = Signal(8)
        self.dataBusIn = Signal(8)
        self.dataBusOut = Signal(8)

        self.offset = Signal(8)
        self.input2 = Signal(8)
        self.carry = Signal()
        self.hibyte = Signal()
        self.result = Signal(9)

    def ports(self):
        return [self.input, self.dataBusIn, self.dataBusOut]

    def elaborate(self, platform):
        m = Module()

        with m.If(self.controls.writeRegister8 == Register8.OFFSET):
            m.d.pos += self.offset.eq(self.dataBusIn)

        with m.If(self.controls.readRegister8 != Register8.ADDR_ALU):
            m.d.pos += self.carry.eq(0)
            m.d.pos += self.hibyte.eq(0)
        with m.Else():
            m.d.pos += self.carry.eq(self.result[8])
            m.d.pos += self.hibyte.eq(1)

        with m.If(self.hibyte == 0):
            m.d.comb += self.input2.eq(self.offset)
        with m.Else():
            m.d.comb += self.input2.eq(Mux(self.offset[7], 0xFF, 0x00))

        m.d.comb += self.result.eq(self.input2 + self.input + self.carry)

        with m.If(self.controls.readRegister8 == Register8.ADDR_ALU):
            m.d.comb += self.dataBusOut.eq(self.result[0:8])
        with m.Else():
            m.d.comb += self.dataBusOut.eq(0)

        if platform == "formal":
            self.formal(m)

        return m

    def formal(self, m):
        rst = ResetSignal(domain="pos")
        loadOffset = Signal()
        continueAdd = Signal()

        m.d.comb += loadOffset.eq(
            self.controls.writeRegister8 == Register8.OFFSET)
        m.d.comb += continueAdd.eq(self.controls.addrALUInputByte == 1)

        loadedOffset = Signal(8)
        m.d.comb += loadedOffset.eq(Past(self.dataBusIn, 2))

        inputLow = Signal(8)
        inputHigh = Signal(8)
        m.d.comb += inputLow.eq(Past(self.input))
        m.d.comb += inputHigh.eq(self.input)
        input16 = Cat(inputLow, inputHigh)

        offsetLow = Signal(8)
        offsetHigh = Signal(8)
        m.d.comb += offsetLow.eq(Past(self.dataBusIn, 2))
        m.d.comb += offsetHigh.eq(Mux(offsetLow[7], 0xFF, 0x00))
        offset16 = Cat(offsetLow, offsetHigh)

        outputLow = Signal(8)
        outputHigh = Signal(8)
        m.d.comb += outputLow.eq(Past(self.dataBusOut))
        m.d.comb += outputHigh.eq(self.dataBusOut)
        output16 = Cat(outputLow, outputHigh)

        m.d.comb += Assume(~(loadOffset & continueAdd))

        with m.If(~Past(rst, 2) & ~Past(rst) & ~rst):
            # Remember that a signal Fell n clocks ago if if was high
            # n+1 clocks ago and was low n clocks ago:
            # Fell(x, n) == Past(x, n+1) & ~Past(x, n)
            with m.If(
                    Fell(loadOffset, 1) & ~loadOffset
                    & Rose(continueAdd, 1) & Fell(continueAdd)):
                m.d.comb += Assert(Past(self.offset) == loadedOffset)
                m.d.comb += Assert(output16 == (input16 + offset16)[0:16])


if __name__ == "__main__":
    clk = Signal()
    rst = Signal()

    pos = ClockDomain()
    pos.clk = clk
    pos.rst = rst

    alu = AddrALU()

    m = Module()
    m.domains.pos = pos
    m.submodules.alu = alu

    main(m, ports=[clk, rst] + alu.ports(), platform="formal")
