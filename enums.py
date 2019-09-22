from enum import Enum, unique
from nmigen import *
from nmigen.cli import main
from nmigen.asserts import *


@unique
class MCycle(Enum):
    NONE = 0
    M1 = 1
    MEM = 2
    IO = 3
    _next = 4

    @classmethod
    def signal(cls):
        return Signal.range(0, MCycle._next.value - 1)

    @property
    def const(self):
        return Const(self.value, MCycle.signal().shape())


class MCycler(Elaboratable):
    def __init__(self):
        self.mcycle = MCycle.signal()

    def ports(self):
        return [self.mcycle]

    def elaborate(self, platform):
        m = Module()
        m.d.pos += self.mcycle.eq(MCycle.M1.const)
        return m


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
