from nmigen import *
from nmigen.cli import main
from nmigen.asserts import *


class TransparentLatch(Elaboratable):
    def __init__(self, width):
        self.input = Signal(width)
        self.output = Signal(width)
        self.x = Signal(width)

        # en indicates that input should go to output.
        # when en is disabled, then x goes to the output. As long
        # as there was a positive clock edge while en was high,
        # the input will be stored in x.
        self.en = Signal()

    def ports(self):
        return [self.input, self.output, self.en]

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.output.eq(Mux(self.en, self.input, self.x))
        with m.If(self.en):
            m.d.pos += self.x.eq(self.input)

        if platform == "formal":
            self.formal(m)

        return m

    def formal(self, m: Module):
        rst = ResetSignal("pos")
        with m.If(Fell(self.en) & ~Past(rst) & ~rst):
            m.d.comb += Assert(self.x == self.output)
            m.d.comb += Assert(self.x == Past(self.input))
        with m.If(self.en & ~Past(rst) & ~rst):
            m.d.comb += Assert(self.output == self.input)


if __name__ == "__main__":
    clk = Signal()
    rst = Signal()

    pos = ClockDomain()
    pos.clk = clk
    pos.rst = rst

    latch = TransparentLatch(8)

    m = Module()
    m.domains.pos = pos
    m.submodules.latch = latch

    main(m, ports=[clk, rst] + latch.ports(), platform="formal")
