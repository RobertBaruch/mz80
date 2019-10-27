from nmigen import *
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

        m.d.comb += self.spec.valid.eq(
            self.actual.valid & self.actual.instr.matches("00---110"))

        m.d.comb += [
            self.spec.regs_out.eq(self.actual.regs_out),
            self.spec.useIX.eq(self.actual.useIX),
            self.spec.useIY.eq(self.actual.useIY),
        ]

        with m.If(r != 6):
            m.d.comb += [
                regs_out_r(self.spec, r).eq(n),
                self.spec.regs_out.PC.eq(self.actual.regs_in.PC + 2),
                self.spec.mcycles.num.eq(2),
                self.spec.mcycles.type1.eq(MCycle.M1),
                self.spec.mcycles.tcycles1.eq(4),
                self.spec.mcycles.type2.eq(MCycle.MEMRD),
                self.spec.mcycles.tcycles2.eq(3),
                self.spec.memwrs.num.eq(0),
            ]
        with m.Elif(~self.actual.useIX & ~self.actual.useIY):
            m.d.comb += [
                self.spec.regs_out.PC.eq(self.actual.regs_in.PC + 2),
                self.spec.mcycles.num.eq(3),
                self.spec.mcycles.type1.eq(MCycle.M1),
                self.spec.mcycles.tcycles1.eq(4),
                self.spec.mcycles.type2.eq(MCycle.MEMRD),
                self.spec.mcycles.tcycles2.eq(3),
                self.spec.mcycles.type3.eq(MCycle.MEMWR),
                self.spec.mcycles.tcycles3.eq(3),
                self.spec.memwrs.num.eq(1),
                self.spec.memwrs.addr0.eq(
                    Cat(self.actual.regs_in.L1, self.actual.regs_in.H1)),
                self.spec.memwrs.data0.eq(n),
            ]
        with m.Else():
            offset8 = self.actual.operands.data0
            offset = Cat(offset8, Repl(offset8[7], 8))  # sign extend
            n = self.actual.operands.data1
            addr = Mux(self.actual.useIX, self.actual.regs_in.IX,
                       self.actual.regs_in.IY)
            addr += offset
            m.d.comb += [
                self.spec.regs_out.PC.eq(self.actual.regs_in.PC + 3),
                self.spec.mcycles.num.eq(4),
                self.spec.mcycles.type1.eq(MCycle.M1),
                self.spec.mcycles.tcycles1.eq(4),
                self.spec.mcycles.type2.eq(MCycle.MEMRD),
                self.spec.mcycles.tcycles2.eq(3),
                self.spec.mcycles.type3.eq(MCycle.MEMRD),
                self.spec.mcycles.tcycles3.eq(5),
                self.spec.mcycles.type4.eq(MCycle.MEMWR),
                self.spec.mcycles.tcycles4.eq(3),
                self.spec.memwrs.num.eq(1),
                self.spec.memwrs.addr0.eq(addr),
                self.spec.memwrs.data0.eq(n),
            ]

        return m

    def coverage(self, m):
        return [
            Cover(self.spec.valid & (self.actual.instr[3:6] != 6)),
            Cover(self.spec.valid & (self.actual.instr[3:6] == 6) &
                  (~self.actual.useIX & ~self.actual.useIY)),
            Cover(self.spec.valid & (self.actual.instr[3:6] == 6) &
                  (self.actual.useIX == 1)),
        ]
