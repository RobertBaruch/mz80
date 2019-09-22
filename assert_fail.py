from nmigen import *
from nmigen.cli import main
from nmigen.asserts import *


class Failme(Elaboratable):
    def __init__(self):
        pass

    def elaborate(self, platform):
        m = Module()

        cycle = Signal(8, reset_less=True)
        rst = ResetSignal("pos")

        # m.d.comb += rst.eq(cycle < 2)
        # m.d.comb += ResetSignal("pos").eq(cycle < 2)
        m.d.comb += Assume(ResetSignal("pos") == (cycle < 2))
        m.d.pos += cycle.eq(cycle + (cycle != 255))

        with m.If(rst == 0):
            m.d.comb += Assert(cycle >= 2)
            m.d.comb += Cover(cycle > 5)

        return m


if __name__ == "__main__":
    clk = Signal()
    rst = Signal()

    pos = ClockDomain()
    pos.clk = clk
    pos.rst = rst

    failme = Failme()

    m = Module()
    m.domains.pos = pos
    m.submodules.failme = failme

    main(m, ports=[clk, rst], platform="formal")
