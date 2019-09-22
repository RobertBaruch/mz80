from nmigen import *
from nmigen.cli import main
from nmigen.asserts import *
from nmigen.hdl.rec import *

from enum import Enum, unique
from ..core.muxing import MCycle


class Z80fiInterface(Record):
    def __init__(self, name=None):
        super().__init__(
            Layout([
                ("control", Z80fiControlsLayout(), DIR_FANOUT),
                ("registers", RegRecordLayout(DIR_FANOUT), DIR_FANOUT),
                ("bus", BusLayout(), DIR_FANOUT),
            ]),
            name=name)


class Z80fiControlsLayout(Layout):
    def __init__(self):
        super().__init__([
            ("clear", 1, DIR_FANOUT),
            ("add_operand", 1, DIR_FANOUT),
            ("add_memrd_access", 1, DIR_FANOUT),
            ("add_memwr_access", 1, DIR_FANOUT),
            ("add_iord_access", 1, DIR_FANOUT),
            ("add_iowr_access", 1, DIR_FANOUT),
            ("add_tcycle", 1, DIR_FANOUT),
            ("add_mcycle", Signal.enum(MCycle).shape(), DIR_FANOUT),
            ("save_registers_in", 1, DIR_FANOUT),
            ("save_registers_out", 1, DIR_FANOUT),
            ("save_instruction", 1, DIR_FANOUT),
            ("set_valid", 1, DIR_FANOUT),
            ("data", 8, DIR_FANOUT),
            ("addr", 16, DIR_FANOUT),
            ("instr", 8, DIR_FANOUT),
            ("useIX", 1, DIR_FANOUT),
            ("useIY", 1, DIR_FANOUT),
        ])


class BusLayout(Layout):
    def __init__(self):
        super().__init__([
            ("data", 8, DIR_FANOUT),
            ("addr", 16, DIR_FANOUT),
        ])


class RegRecordLayout(Layout):
    def __init__(self, direction=DIR_NONE):
        super().__init__([
            ("A1", 8, direction),
            ("F1", 8, direction),
            ("B1", 8, direction),
            ("C1", 8, direction),
            ("D1", 8, direction),
            ("E1", 8, direction),
            ("H1", 8, direction),
            ("L1", 8, direction),
            ("W1", 8, direction),
            ("Z1", 8, direction),
            ("A2", 8, direction),
            ("F2", 8, direction),
            ("B2", 8, direction),
            ("C2", 8, direction),
            ("D2", 8, direction),
            ("E2", 8, direction),
            ("H2", 8, direction),
            ("L2", 8, direction),
            ("W2", 8, direction),
            ("Z2", 8, direction),
            ("IX", 16, direction),
            ("IY", 16, direction),
            ("SP", 16, direction),
            ("PC", 16, direction),
        ])


class Z80fiState(Record):
    def __init__(self, name=None):
        super().__init__(
            Layout([("valid", 1, DIR_FANIN), ("instr", 8, DIR_FANIN),
                    ("useIX", 1, DIR_FANIN), ("useIY", 1, DIR_FANIN),
                    ("operands", OperandLayout(), DIR_FANIN),
                    ("regs_in", RegRecordLayout(DIR_FANIN), DIR_FANIN),
                    ("regs_out", RegRecordLayout(DIR_FANIN), DIR_FANIN),
                    ("memrds", AccessLayout(), DIR_FANIN),
                    ("memwrs", AccessLayout(), DIR_FANIN),
                    ("iords", AccessLayout(), DIR_FANIN),
                    ("iowrs", AccessLayout(), DIR_FANIN),
                    ("mcycles", CycleLayout(), DIR_FANIN)]),
            name=name)

    def regs_in_r(self, r):
        return self._reg_r(r, self.regs_in)

    def regs_out_r(self, r):
        return self._reg_r(r, self.regs_out)

    def _reg_r(self, r, regs):
        return Array([
            regs.B1, regs.C1, regs.D1, regs.E1, regs.H1, regs.L1,
            Signal(8), regs.A1
        ])[r]


class Z80fiInstrState(Elaboratable):
    def __init__(self):
        # The interface to set the signals
        self.iface = Z80fiInterface(name="iface")
        self.data = Z80fiState()
        self.instr_state = Z80fiState()

    def elaborate(self, platform):
        m = Module()

        m.submodules.operands = self.operands = Z80fiOperands()
        m.submodules.regs_in = self.regs_in = Z80fiRegisters(
            AccessType.REGS_IN)
        m.submodules.regs_out = self.regs_out = Z80fiRegisters(
            AccessType.REGS_OUT)
        m.submodules.mem_rds = self.mem_rds = Z80fiExtAccess(AccessType.MEMRD)
        m.submodules.mem_wrs = self.mem_wrs = Z80fiExtAccess(AccessType.MEMWR)
        m.submodules.io_rds = self.io_rds = Z80fiExtAccess(AccessType.IORD)
        m.submodules.io_wrs = self.io_wrs = Z80fiExtAccess(AccessType.IOWR)
        m.submodules.mcycles = self.mcycles = Z80fiCycles()

        m.d.comb += self.iface.connect(self.operands.iface, self.regs_in.iface,
                                       self.regs_out.iface, self.mem_rds.iface,
                                       self.mem_wrs.iface, self.io_rds.iface,
                                       self.io_wrs.iface, self.mcycles.iface)
        m.d.comb += self.data.connect(
            self.operands.data, self.regs_in.data, self.regs_out.data,
            self.mem_rds.data, self.mem_wrs.data, self.io_rds.data,
            self.io_wrs.data, self.instr_state, self.mcycles.data)

        with m.If(self.iface.control.clear):
            m.d.pos += self.instr_state.valid.eq(0)
        with m.If(self.iface.control.set_valid):
            m.d.pos += self.instr_state.valid.eq(1)
        with m.If(self.iface.control.save_instruction):
            m.d.pos += [
                self.instr_state.instr.eq(self.iface.control.instr),
                self.instr_state.useIX.eq(self.iface.control.useIX),
                self.instr_state.useIY.eq(self.iface.control.useIY),
            ]

        return m


class OperandLayout(Layout):
    def __init__(self):
        super().__init__([
            ("num", 2, DIR_FANIN),
            ("data0", 8, DIR_FANIN),
            ("data1", 8, DIR_FANIN),
            ("data2", 8, DIR_FANIN),
        ])


class Z80fiOperands(Elaboratable):
    def __init__(self):
        self.iface = Z80fiInterface()
        self.data = Z80fiState()

    def elaborate(self, platform):
        m = Module()
        operand = self.iface.control.data

        with m.If(self.iface.control.add_operand):
            with m.Switch(self.data.operands.num):
                with m.Case(0):
                    m.d.pos += self.data.operands.data0.eq(operand)
                    m.d.pos += self.data.operands.num.eq(1)
                with m.Case(1):
                    m.d.pos += self.data.operands.data1.eq(operand)
                    m.d.pos += self.data.operands.num.eq(2)
                with m.Case(2):
                    m.d.pos += self.data.operands.data2.eq(operand)
                    m.d.pos += self.data.operands.num.eq(3)
        with m.If(self.iface.control.clear):
            m.d.pos += self.data.operands.num.eq(0)

        return m


class AccessLayout(Layout):
    def __init__(self):
        super().__init__([
            ("num", 2, DIR_FANIN),
            ("addr0", 16, DIR_FANIN),
            ("data0", 8, DIR_FANIN),
            ("addr1", 16, DIR_FANIN),
            ("data1", 8, DIR_FANIN),
            ("addr2", 16, DIR_FANIN),
            ("data2", 8, DIR_FANIN),
        ])


@unique
class AccessType(Enum):
    MEMRD = 1
    MEMWR = 2
    IORD = 3
    IOWR = 4
    REGS_IN = 5
    REGS_OUT = 6


class Z80fiExtAccess(Elaboratable):
    def __init__(self, access_type):
        self.iface = Z80fiInterface()
        self.data = Z80fiState()
        self.access_type = access_type

    def elaborate(self, platform):
        m = Module()
        addr = self.iface.control.addr
        data = self.iface.control.data

        if self.access_type == AccessType.MEMRD:
            accessed = self.iface.control.add_memrd_access
            store = self.data.memrds
        elif self.access_type == AccessType.MEMWR:
            accessed = self.iface.control.add_memwr_access
            store = self.data.memwrs
        elif self.access_type == AccessType.IORD:
            accessed = self.iface.control.add_iord_access
            store = self.data.iords
        elif self.access_type == AccessType.IOWR:
            accessed = self.iface.control.add_iowr_access
            store = self.data.iowrs

        with m.If(accessed):
            with m.Switch(store.num):
                with m.Case(0):
                    m.d.pos += store.addr0.eq(addr)
                    m.d.pos += store.data0.eq(data)
                    m.d.pos += store.num.eq(1)
                with m.Case(1):
                    m.d.pos += store.addr1.eq(addr)
                    m.d.pos += store.data1.eq(data)
                    m.d.pos += store.num.eq(2)
                with m.Case(2):
                    m.d.pos += store.addr2.eq(addr)
                    m.d.pos += store.data2.eq(data)
                    m.d.pos += store.num.eq(3)
        with m.If(self.iface.control.clear):
            m.d.pos += store.num.eq(0)

        return m


class Z80fiRegisters(Elaboratable):
    def __init__(self, access_type):
        self.iface = Z80fiInterface()
        self.data = Z80fiState()
        self.access_type = access_type

    def elaborate(self, platform):
        m = Module()

        if self.access_type == AccessType.REGS_IN:
            accessed = self.iface.control.save_registers_in
            store = self.data.regs_in
        elif self.access_type == AccessType.REGS_OUT:
            accessed = self.iface.control.save_registers_out
            store = self.data.regs_out

        with m.If(accessed):
            m.d.pos += store.eq(self.iface.registers)

        return m


class CycleLayout(Layout):
    def __init__(self):
        super().__init__([
            ("num", 3, DIR_FANIN),
            ("type1", Signal.enum(MCycle).shape(), DIR_FANIN),
            ("tcycles1", 3, DIR_FANIN),
            ("type2", Signal.enum(MCycle).shape(), DIR_FANIN),
            ("tcycles2", 3, DIR_FANIN),
            ("type3", Signal.enum(MCycle).shape(), DIR_FANIN),
            ("tcycles3", 3, DIR_FANIN),
            ("type4", Signal.enum(MCycle).shape(), DIR_FANIN),
            ("tcycles4", 3, DIR_FANIN),
            ("type5", Signal.enum(MCycle).shape(), DIR_FANIN),
            ("tcycles5", 3, DIR_FANIN),
            ("type6", Signal.enum(MCycle).shape(), DIR_FANIN),
            ("tcycles6", 3, DIR_FANIN),
        ])


class Z80fiCycles(Elaboratable):
    def __init__(self):
        self.iface = Z80fiInterface()
        self.data = Z80fiState()

    def elaborate(self, platform):
        m = Module()
        mcycles = self.data.mcycles
        control = self.iface.control

        with m.If(control.clear):
            m.d.pos += mcycles.num.eq(0)

        with m.If(control.add_tcycle):
            with m.Switch(mcycles.num):
                with m.Case(1):
                    m.d.pos += mcycles.tcycles1.eq(mcycles.tcycles1 + 1)
                with m.Case(2):
                    m.d.pos += mcycles.tcycles2.eq(mcycles.tcycles2 + 1)
                with m.Case(3):
                    m.d.pos += mcycles.tcycles3.eq(mcycles.tcycles3 + 1)
                with m.Case(4):
                    m.d.pos += mcycles.tcycles4.eq(mcycles.tcycles4 + 1)
                with m.Case(5):
                    m.d.pos += mcycles.tcycles5.eq(mcycles.tcycles5 + 1)
                with m.Case(6):
                    m.d.pos += mcycles.tcycles6.eq(mcycles.tcycles6 + 1)

        with m.If(control.add_mcycle != MCycle.NONE):
            with m.If(mcycles.num < 6):
                with m.Switch(mcycles.num):
                    with m.Case(0):
                        # Because instruction state can only be finalized during
                        # M1 T1 of the next instruction, we register M1 cycles
                        # on M1 T2.
                        m.d.pos += mcycles.type1.eq(control.add_mcycle)
                        m.d.pos += mcycles.tcycles1.eq(2)
                    with m.Case(1):
                        m.d.pos += mcycles.type2.eq(control.add_mcycle)
                        m.d.pos += mcycles.tcycles2.eq(1)
                    with m.Case(2):
                        m.d.pos += mcycles.type3.eq(control.add_mcycle)
                        m.d.pos += mcycles.tcycles3.eq(1)
                    with m.Case(3):
                        m.d.pos += mcycles.type4.eq(control.add_mcycle)
                        m.d.pos += mcycles.tcycles4.eq(1)
                    with m.Case(4):
                        m.d.pos += mcycles.type5.eq(control.add_mcycle)
                        m.d.pos += mcycles.tcycles5.eq(1)
                    with m.Case(5):
                        m.d.pos += mcycles.type6.eq(control.add_mcycle)
                        m.d.pos += mcycles.tcycles6.eq(1)

                m.d.pos += mcycles.num.eq(mcycles.num + 1)

        return m
