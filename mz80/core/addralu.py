from enum import Enum, unique
from nmigen import *
from nmigen.cli import main
from nmigen.asserts import *


class AddrALU(Elaboratable):
    """An 8-bit ALU that only adds and has a carry.
    """

    def __init__(self):
        self.input = Signal(8)
        self.dataBus = Signal(8)
        self.output = Signal(8)

        # ALU commands.
        # loadOffset copies the dataBus into offset, and zeroes the carry.
        self.loadOffset = Signal()
        # continueAdd loads the offset with FF or 00 depending on offset's sign,
        # and does an add-with-carry.
        self.continueAdd = Signal()

        self.offset = Signal(8)
        self.carry = Signal()
        self.result = Signal(9)

    def ports(self):
        return [
            self.input, self.dataBus, self.output, self.loadOffset,
            self.continueAdd
        ]

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.result.eq(self.offset + self.input + self.carry)
        m.d.comb += self.output.eq(self.result[0:8])

        with m.If(self.loadOffset):
            m.d.pos += self.offset.eq(self.dataBus)
            m.d.pos += self.carry.eq(0)
        with m.Elif(self.continueAdd):
            m.d.pos += self.offset.eq(Mux(self.offset[7], 0xFF, 0x00))
            m.d.pos += self.carry.eq(self.result[8])

        if platform == "formal":
            self.formal(m)

        return m

    def formal(self, m):
        rst = ResetSignal(domain="pos")

        loadedOffset = Signal(8)
        m.d.comb += loadedOffset.eq(Past(self.dataBus, 2))

        inputLow = Signal(8)
        inputHigh = Signal(8)
        m.d.comb += inputLow.eq(Past(self.input))
        m.d.comb += inputHigh.eq(self.input)
        input16 = Cat(inputLow, inputHigh)

        offsetLow = Signal(8)
        offsetHigh = Signal(8)
        m.d.comb += offsetLow.eq(Past(self.dataBus, 2))
        m.d.comb += offsetHigh.eq(Mux(offsetLow[7], 0xFF, 0x00))
        offset16 = Cat(offsetLow, offsetHigh)

        outputLow = Signal(8)
        outputHigh = Signal(8)
        m.d.comb += outputLow.eq(Past(self.output))
        m.d.comb += outputHigh.eq(self.output)
        output16 = Cat(outputLow, outputHigh)

        m.d.comb += Assume(~(self.loadOffset & self.continueAdd))

        with m.If(~Past(rst, 2) & ~Past(rst) & ~rst):
            # Remember that a signal Fell n clocks ago if if was high
            # n+1 clocks ago and was low n clocks ago:
            # Fell(x, n) == Past(x, n+1) & ~Past(x, n)
            with m.If(
                    Fell(self.loadOffset, 1) & ~self.loadOffset
                    & Rose(self.continueAdd, 1) & Fell(self.continueAdd)):
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
