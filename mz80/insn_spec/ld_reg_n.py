from nmigen import *
from nmigen.cli import main
from nmigen.asserts import *
from ..core.z80 import Z80
from ..core.muxing import MCycle
from ..z80fi.z80fi import *


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

        m.d.comb += [
            self.spec.useIX.eq(self.actual.useIX),
            self.spec.useIY.eq(self.actual.useIY),
            self.spec.regs_out.eq(self.actual.regs_out),
            regs_out_r(self.spec, r).eq(n),
            self.spec.regs_out.PC.eq(self.actual.regs_in.PC + 2),
            self.spec.mcycles.num.eq(2),
            self.spec.mcycles.type1.eq(MCycle.M1),
            self.spec.mcycles.tcycles1.eq(4),
            self.spec.mcycles.type2.eq(MCycle.MEMRD),
            self.spec.mcycles.tcycles2.eq(3),
        ]
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
    count = Signal.range(0, 61)

    with m.If(count < 60):
        m.d.pos += count.eq(count + 1)

    m.d.comb += z80.z80fi.connect(state.iface)
    m.d.comb += actual.connect(state.data)
    m.d.comb += test.actual.connect(state.data)
    m.d.comb += spec.connect(test.spec)

    m.d.comb += Cover(spec.valid)
    # m.d.comb += Cover((count == 59) & spec.valid)
    with m.If(spec.valid):
        m.d.comb += [
            Assert(spec.regs_out.A1 == actual.regs_out.A1),
            Assert(spec.regs_out.A2 == actual.regs_out.A2),
            Assert(spec.regs_out.F1 == actual.regs_out.F1),
            Assert(spec.regs_out.F2 == actual.regs_out.F2),
            Assert(spec.regs_out.B1 == actual.regs_out.B1),
            Assert(spec.regs_out.B2 == actual.regs_out.B2),
            Assert(spec.regs_out.C1 == actual.regs_out.C1),
            Assert(spec.regs_out.C2 == actual.regs_out.C2),
            Assert(spec.regs_out.D1 == actual.regs_out.D1),
            Assert(spec.regs_out.D2 == actual.regs_out.D2),
            Assert(spec.regs_out.E1 == actual.regs_out.E1),
            Assert(spec.regs_out.E2 == actual.regs_out.E2),
            Assert(spec.regs_out.H1 == actual.regs_out.H1),
            Assert(spec.regs_out.H2 == actual.regs_out.H2),
            Assert(spec.regs_out.L1 == actual.regs_out.L1),
            Assert(spec.regs_out.L2 == actual.regs_out.L2),
            Assert(spec.regs_out.IX == actual.regs_out.IX),
            Assert(spec.regs_out.IY == actual.regs_out.IY),
            Assert(spec.regs_out.SP == actual.regs_out.SP),
            Assert(spec.regs_out.PC == actual.regs_out.PC),
            Assert(spec.mcycles.num == actual.mcycles.num),
        ]
        with m.If(spec.mcycles.num >= 1):
            m.d.comb += [
                Assert(spec.mcycles.tcycles1 == actual.mcycles.tcycles1),
                Assert(spec.mcycles.type1 == actual.mcycles.type1),
            ]
        with m.If(spec.mcycles.num >= 2):
            m.d.comb += [
                Assert(spec.mcycles.tcycles2 == actual.mcycles.tcycles2),
                Assert(spec.mcycles.type2 == actual.mcycles.type2),
            ]
        with m.If(spec.mcycles.num >= 3):
            m.d.comb += [
                Assert(spec.mcycles.tcycles3 == actual.mcycles.tcycles3),
                Assert(spec.mcycles.type3 == actual.mcycles.type3),
            ]
        with m.If(spec.mcycles.num >= 4):
            m.d.comb += [
                Assert(spec.mcycles.tcycles4 == actual.mcycles.tcycles4),
                Assert(spec.mcycles.type4 == actual.mcycles.type4),
            ]
        with m.If(spec.mcycles.num >= 5):
            m.d.comb += [
                Assert(spec.mcycles.tcycles5 == actual.mcycles.tcycles5),
                Assert(spec.mcycles.type5 == actual.mcycles.type5),
            ]
        with m.If(spec.mcycles.num >= 6):
            m.d.comb += [
                Assert(spec.mcycles.tcycles6 == actual.mcycles.tcycles6),
                Assert(spec.mcycles.type6 == actual.mcycles.type6),
            ]

    main(m, ports=[clk, rst] + z80.ports())
