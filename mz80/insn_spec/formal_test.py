import importlib

from nmigen import *
from nmigen.cli import main_parser, main_runner
from nmigen.asserts import *
from ..core.z80 import Z80
from ..z80fi.z80fi import *


if __name__ == "__main__":
    parser = main_parser()
    parser.add_argument("--cover", action="store_true")
    parser.add_argument("--bmc", action="store_true")
    parser.add_argument("--insn")
    args = parser.parse_args()

    clk = Signal()
    rst = Signal()

    pos = ClockDomain()
    pos.clk = clk
    pos.rst = rst

    neg = ClockDomain(clk_edge="neg")
    neg.clk = clk
    neg.rst = rst

    m = Module()
    m.domains.pos = pos
    m.domains.neg = neg
    m.submodules.z80 = z80 = Z80(include_z80fi=True)
    m.submodules.state = state = Z80fiInstrState()

    assert args.insn is not None, "No --insn specified"

    insn_spec = importlib.import_module("." + args.insn, package="mz80.insn_spec")
    klass = getattr(insn_spec, args.insn)

    m.submodules.test = test = klass()

    actual = Z80fiState()
    spec = Z80fiState()
    count = Signal.range(0, 61, reset_less=True)

    with m.If(count < 60):
        m.d.pos += count.eq(count + 1)

    m.d.comb += Assume(z80.nBUSRQ == 1)
    m.d.comb += Assume(z80.nINTRQ == 1)
    m.d.comb += Assume(ResetSignal("pos") == (count < 4))

    m.d.comb += z80.z80fi.connect(state.iface)
    m.d.comb += actual.connect(state.data)
    m.d.comb += test.actual.connect(state.data)
    m.d.comb += spec.connect(test.spec)

    if args.cover:
        m.d.comb += test.coverage(m)
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
            Assert(spec.memwrs.num == actual.memwrs.num),
        ]

        if args.cover:
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

            with m.If(spec.memwrs.num >= 1):
                m.d.comb += [
                    Assert(spec.memwrs.addr0 == actual.memwrs.addr0),
                    Assert(spec.memwrs.data0 == actual.memwrs.data0),
                ]
            with m.If(spec.memwrs.num >= 2):
                m.d.comb += [
                    Assert(spec.memwrs.addr1 == actual.memwrs.addr1),
                    Assert(spec.memwrs.data1 == actual.memwrs.data1),
                ]
            with m.If(spec.memwrs.num >= 3):
                m.d.comb += [
                    Assert(spec.memwrs.addr2 == actual.memwrs.addr2),
                    Assert(spec.memwrs.data2 == actual.memwrs.data2),
                ]

    main_runner(parser, args, m, ports=[clk, rst] + z80.ports())
    # main(m, ports=[clk, rst] + z80.ports())
