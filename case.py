from nmigen import *
from nmigen.cli import main


class MCycler(Elaboratable):
    def __init__(self):
        self.mcycle = Signal(3)
        self.requested_cycle = Signal(3)
        self.switcher = Signal()

    def ports(self):
        return [self.mcycle]

    def elaborate(self, platform):
        m = Module()
        with m.If(self.switcher):
            self.setCycle(m, self.requested_cycle)
        with m.Else():
            self.setCycle(m, 0)
        return m

    def setCycle(self, m, cycle):
        with m.Switch(cycle):
            with m.Case(2):
                m.d.pos += self.mcycle.eq(0)
            with m.Default():
                m.d.pos += self.mcycle.eq(4)


if __name__ == "__main__":
    clk = Signal()
    rst = Signal()

    pos = ClockDomain()
    pos.clk = clk
    pos.rst = rst

    cycler = MCycler()

    m = Module()
    m.domains.pos = pos
    m.submodules.cycler = cycler

    main(m, ports=[clk, rst] + cycler.ports(), platform="formal")
