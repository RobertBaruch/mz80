from nmigen import *
from nmigen.asserts import *
from ..core.z80 import Z80
from ..core.muxing import MCycle
from ..z80fi.z80fi import *


class ld_reg_reg(Elaboratable):
    def __init__(self):
        self.actual = Z80fiState(name="actual")
        self.spec = Z80fiState(name="spec")

    def elaborate(self, platform):
        m = Module()

        dst_r = self.actual.instr[3:6]
        src_r = self.actual.instr[0:3]

        m.d.comb += self.spec.valid.eq(
            self.actual.valid & self.actual.instr.matches("01------"))

        m.d.comb += [
            self.spec.regs_out.eq(self.actual.regs_out),
            self.spec.useIX.eq(self.actual.useIX),
            self.spec.useIY.eq(self.actual.useIY),
        ]

        with m.If((dst_r != 6) & (src_r != 6)): # LD r, r
            m.d.comb += [
                regs_out_r(self.spec, dst_r).eq(regs_in_r(self.actual, src_r)),
                self.spec.regs_out.PC.eq(self.actual.regs_in.PC + 1),

                self.spec.mcycles.num.eq(1),
                self.spec.mcycles.type1.eq(MCycle.M1),
                self.spec.mcycles.tcycles1.eq(4),
                self.spec.memwrs.num.eq(0),
            ]

        with m.Elif((dst_r == 6) & (src_r == 6)): # HALT
            m.d.comb += [
                self.spec.mcycles.num.eq(2),
                self.spec.mcycles.type1.eq(MCycle.M1),
                self.spec.mcycles.tcycles1.eq(4),
                self.spec.mcycles.type2.eq(MCycle.M1),
                self.spec.mcycles.tcycles2.eq(4),
                self.spec.memwrs.num.eq(0),
            ]

        with m.Elif(~self.actual.useIX & ~self.actual.useIY):
            with m.If(src_r == 6): # LD r, (HL)
                m.d.comb += [
                    self.spec.regs_out.PC.eq(self.actual.regs_in.PC + 1),
                    self.spec.memrds.num.eq(1),
                    self.spec.memrds.addr0.eq(
                        Cat(self.actual.regs_in.L1, self.actual.regs_in.H1)),
                    regs_out_r(self.spec, dst_r).eq(self.actual.memrds.data0),

                    self.spec.mcycles.num.eq(2),
                    self.spec.mcycles.type1.eq(MCycle.M1),
                    self.spec.mcycles.tcycles1.eq(4),
                    self.spec.mcycles.type2.eq(MCycle.MEMRD),
                    self.spec.mcycles.tcycles2.eq(3),
                ]
            with m.Else(): # LD (HL), r
                m.d.comb += [
                    self.spec.regs_out.PC.eq(self.actual.regs_in.PC + 1),
                    self.spec.memwrs.num.eq(1),
                    self.spec.memwrs.addr0.eq(
                        Cat(self.actual.regs_in.L1, self.actual.regs_in.H1)),
                    self.spec.memwrs.data0.eq(regs_in_r(self.actual, src_r)),

                    self.spec.mcycles.num.eq(2),
                    self.spec.mcycles.type1.eq(MCycle.M1),
                    self.spec.mcycles.tcycles1.eq(4),
                    self.spec.mcycles.type2.eq(MCycle.MEMWR),
                    self.spec.mcycles.tcycles2.eq(3),
                ]

        with m.Else():
            offset8 = self.actual.operands.data0
            offset = Cat(offset8, Repl(offset8[7], 8))  # sign extend
            addr = Mux(self.actual.useIX, self.actual.regs_in.IX,
                       self.actual.regs_in.IY)
            addr += offset
            m.d.comb += [
                self.spec.regs_out.PC.eq(self.actual.regs_in.PC + 2),

                self.spec.mcycles.num.eq(4),
                self.spec.mcycles.type1.eq(MCycle.M1),
                self.spec.mcycles.tcycles1.eq(4),
                self.spec.mcycles.type2.eq(MCycle.MEMRD),
                self.spec.mcycles.tcycles2.eq(3),
                self.spec.mcycles.type3.eq(MCycle.INTERNAL),
                self.spec.mcycles.tcycles3.eq(5),
            ]
            with m.If(src_r == 6): # LD r, (IX+d)
                m.d.comb += [
                    self.spec.memrds.num.eq(1),
                    self.spec.memrds.addr0.eq(addr),
                    regs_out_r(self.spec, dst_r).eq(self.actual.memrds.data0),

                    self.spec.mcycles.type4.eq(MCycle.MEMRD),
                    self.spec.mcycles.tcycles4.eq(3),
                ]
            with m.Else(): # LD (IX+d), r
                m.d.comb += [
                    self.spec.memwrs.num.eq(1),
                    self.spec.memwrs.addr0.eq(addr),
                    self.spec.memwrs.data0.eq(regs_in_r(self.actual, src_r)),

                    self.spec.mcycles.type4.eq(MCycle.MEMWR),
                    self.spec.mcycles.tcycles4.eq(3),
                ]

        return m

    def coverage(self, m):
        dst_r = self.actual.instr[3:6]
        src_r = self.actual.instr[0:3]

        return [
            Cover(self.spec.valid & (dst_r != 6) & (src_r != 6)),
            Cover(self.spec.valid & (dst_r == 6) &
                  (~self.actual.useIX & ~self.actual.useIY)),
            Cover(self.spec.valid & (src_r == 6) &
                  (~self.actual.useIX & ~self.actual.useIY)),
            Cover(self.spec.valid & (dst_r == 6) &
                  (self.actual.useIX == 1)),
            Cover(self.spec.valid & (src_r == 6) &
                  (self.actual.useIX == 1)),
        ]
