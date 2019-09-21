from nmigen import *
from nmigen.cli import main
from nmigen.asserts import *
from ..core.z80 import Z80
from ..z80fi.z80fi import Z80fiState, Z80fiInstrState


class ld_reg_n(Elaboratable):
    def __init__(self):
        self.actual = Z80fiState(name="actual")
        self.spec = Z80fiState(name="spec")

    def elaborate(self, platform):
        m = Module()

        r = self.actual.instr[3:6]
        n = self.actual.operands.data0

        m.d.comb += self.spec.valid.eq(self.actual.valid & (
            self.actual.instr.matches("00---110")) & (r != 6))

        m.d.comb += self.spec.regs_out.eq(self.actual.regs_out)
        m.d.comb += self.spec.regs_out_r(r).eq(n)
        return m


if __name__ == "__main__":
    m = Module()

    clk = Signal()
    rst = Signal()

    pos = ClockDomain()
    pos.clk = clk
    pos.rst = rst

    neg = ClockDomain(clk_edge="neg")
    neg.clk = clk
    neg.rst = rst

    m.domains.pos = pos
    m.domains.neg = neg
    m.submodules.z80 = z80 = Z80(include_z80fi=True)
    m.submodules.state = state = Z80fiInstrState()
    m.submodules.test = test = ld_reg_n()

    actual = Z80fiState()
    spec = Z80fiState()
    count = Signal.range(0, 60)

    with m.If(count < 59):
        m.d.pos += count.eq(count + 1)

    m.d.comb += z80.z80fi.connect(state.iface)
    m.d.comb += actual.connect(state.data)
    m.d.comb += test.actual.connect(state.data)
    m.d.comb += spec.connect(test.spec)

    m.d.comb += Cover(spec.valid)
    # m.d.comb += Cover((count == 59) & spec.valid)
    with m.If(spec.valid):
        m.d.comb += Assert(spec.regs_out == actual.regs_out)

    main(m, ports=[clk, rst] + z80.ports())
