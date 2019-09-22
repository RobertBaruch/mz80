from nmigen import *
from nmigen.cli import main
from nmigen.asserts import *


class Thing(Record):
    def __init__(self, name=None):
        super().__init__([
            ("a", 5),
            ("b", 3),
        ], name=name)


class TestCase(Elaboratable):
    def __init__(self):
        self.rec = Thing("thing")
        self.input = Signal(self.rec.shape()[0])
        self.output_a = Signal(5)
        self.output_b = Signal(3)

    def elaborate(self, platform):
        m = Module()
        m.d.comb += self.rec.eq(self.input)
        m.d.comb += self.output_a.eq(self.rec.a)
        m.d.comb += self.output_b.eq(self.rec.b)
        return m


if __name__ == "__main__":
    clk = Signal()
    rst = Signal()

    pos = ClockDomain()
    pos.clk = clk
    pos.rst = rst

    testcase = TestCase()

    m = Module()
    m.domains.pos = pos
    m.submodules.testcase = testcase

    main(
        m,
        ports=[clk, rst, testcase.input, testcase.output_a, testcase.output_b],
        platform="formal")
