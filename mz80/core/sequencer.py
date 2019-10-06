from enum import Enum, unique
from nmigen import *
from nmigen.cli import main
from nmigen.asserts import *

from .muxing import *
from .arch import Registers
from .mcycler import *
from .transparent_latch import TransparentLatch
from ..z80fi.z80fi import Z80fiInterface


class Sequencer(Elaboratable):
    def __init__(self, include_z80fi=False):
        self.cycle_num = Signal.range(0, 10)

        self.dataBusIn = Signal(8)

        self.controls = SequencerControls(name="ctrls")
        self.extended_cycle_controls = SequencerControls(name="extcyc_ctrls")

        self.instr = TransparentLatch(8)

        # Where the data from a memory read should be stored.
        self.memrd_addr = Signal.enum(Register16)
        self.memrd_dest = Signal.enum(Register8)
        self.memwr_addr = Signal.enum(Register16)
        self.memwr_src = Signal.enum(Register8)
        self.useIX = Signal()
        self.useIY = Signal()
        self.registerSet = Signal()

        #
        # Signals going to the mcycler
        #
        self.extend = Signal()
        self.cycle = Signal.enum(MCycle)

        #
        # Signals coming from the mcycler
        #

        # Tells the sequencer that all the actions it set up are to be
        # registered on the positive edge of the clock.
        self.act = Signal()

        self.include_z80fi = include_z80fi
        if self.include_z80fi:
            self.z80fi = Z80fiInterface()

    def ports(self):
        ps = [
            self.extend, self.cycle, self.dataBusIn, self.act,
            self.dataBusSource, self.dataBusDest, self.register8Source,
            self.register16Source, self.register8Dest, self.register16Dest,
            self.addrIncDecSetting
        ]
        if self.include_z80fi:
            ps.extend(self.z80fi.ports())
        return ps

    def elaborate(self, platform):
        m = Module()

        # INSTR register
        m.submodules.instr = self.instr
        m.d.comb += self.instr.input.eq(self.dataBusIn)

        # When the MCycler is waitstated, there will be no act. In any other case,
        # every state transition leads to an act.
        with m.FSM(domain="pos", reset="RESET") as fsm:
            # defaults
            m.d.comb += self.controls.eq(0)
            m.d.comb += self.controls.useIX.eq(self.useIX)
            m.d.comb += self.controls.useIY.eq(self.useIY)
            m.d.comb += self.controls.registerSet.eq(self.registerSet)
            m.d.comb += self.controls.readRegister8.eq(Register8.NONE)
            m.d.comb += self.controls.incR.eq(0)

            if self.include_z80fi:
                m.d.comb += self.z80fi.control.add_operand.eq(0)
                m.d.comb += self.z80fi.control.add_memrd_access.eq(0)
                m.d.comb += self.z80fi.control.add_memwr_access.eq(0)
                m.d.comb += self.z80fi.control.add_iord_access.eq(0)
                m.d.comb += self.z80fi.control.add_iowr_access.eq(0)
                m.d.comb += self.z80fi.control.add_tcycle.eq(0)
                m.d.comb += self.z80fi.control.add_mcycle.eq(MCycle.NONE)
                m.d.comb += self.z80fi.control.save_registers_in.eq(0)
                m.d.comb += self.z80fi.control.save_registers_out.eq(0)
                m.d.comb += self.z80fi.control.save_instruction.eq(0)
                m.d.comb += self.z80fi.control.set_valid.eq(0)
                m.d.comb += self.z80fi.control.clear.eq(0)

            with m.State("RESET"):
                m.d.pos += self.useIX.eq(0)
                m.d.pos += self.useIY.eq(0)
                m.d.pos += self.registerSet.eq(0)
                self.initiateInstructionFetch(m)

            with m.State("M1_T1"):
                m.d.comb += self.controls.readRegister16.eq(Register16.PC)
                m.d.comb += self.controls.readRegister8.eq(
                    Register8.MCYCLER_RDATA)

                if self.include_z80fi:
                    # Take a snapshot of the state. This is the state coming out
                    # of the previous instruction. We want to keep the state going
                    # in to the previous instruction, and we'll load up the state
                    # going in to this instruction on the next cycle.
                    m.d.comb += self.z80fi.control.set_valid.eq(1)
                    m.d.comb += self.z80fi.control.save_registers_out.eq(1)

                m.next = "M1_T2"

            # This state can be waitstated. If waitstated, self.act will be 0.
            with m.State("M1_T2"):
                m.d.comb += self.controls.readRegister16.eq(Register16.PC)
                m.d.comb += self.controls.readRegister8.eq(
                    Register8.MCYCLER_RDATA)

                if self.include_z80fi:
                    m.d.comb += self.z80fi.control.clear.eq(1)
                    m.d.comb += self.z80fi.control.add_mcycle.eq(MCycle.M1)

                with m.If(self.act):
                    m.d.comb += self.controls.addrIncDecSetting.eq(
                        IncDecSetting.INC)
                    m.d.comb += self.controls.writeRegister16.eq(Register16.PC)
                    m.d.pos += self.instr.en.eq(0)

                    # Take a snapshot of the state. This is the state going
                    # in to this instruction. Also the instruction register.
                    if self.include_z80fi:
                        m.d.comb += [
                            self.z80fi.control.save_registers_in.eq(1),
                            self.z80fi.control.save_instruction.eq(1),
                            self.z80fi.control.instr.eq(self.instr.input),
                            self.z80fi.control.useIX.eq(self.controls.useIX),
                            self.z80fi.control.useIY.eq(self.controls.useIY),
                        ]

                    m.next = "M1_T3"

            with m.State("M1_T3"):
                m.d.comb += self.controls.readRegister16.eq(Register16.R)
                if self.include_z80fi:
                    m.d.comb += self.z80fi.control.add_tcycle.eq(1)
                m.next = "M1_T4"

            with m.State("M1_T4"):
                m.d.comb += self.controls.readRegister16.eq(Register16.R)
                m.d.comb += self.controls.incR.eq(1)
                if self.include_z80fi:
                    m.d.comb += self.z80fi.control.add_tcycle.eq(1)
                self.execute(m)

            with m.State("EXTENDED"):
                m.d.comb += self.controls.eq(self.extended_cycle_controls)
                if self.include_z80fi:
                    m.d.comb += self.z80fi.control.add_tcycle.eq(1)
                self.execute(m)

            with m.State("RDOPERAND_T1"):
                m.d.comb += self.controls.readRegister16.eq(Register16.PC)
                m.d.comb += self.controls.readRegister8.eq(
                    Register8.MCYCLER_RDATA)
                if self.include_z80fi:
                    m.d.comb += self.z80fi.control.add_mcycle.eq(MCycle.MEMRD)
                m.next = "RDOPERAND_T2"

            # This state can be waitstated. If waitstated, self.act will be 0.
            with m.State("RDOPERAND_T2"):
                m.d.comb += self.controls.readRegister16.eq(Register16.PC)
                m.d.comb += self.controls.readRegister8.eq(
                    Register8.MCYCLER_RDATA)
                with m.If(self.act):
                    if self.include_z80fi:
                        m.d.comb += self.z80fi.control.add_tcycle.eq(1)
                    m.next = "RDOPERAND_T3"

            with m.State("RDOPERAND_T3"):
                m.d.comb += self.controls.readRegister16.eq(Register16.PC)
                m.d.comb += self.controls.addrIncDecSetting.eq(
                    IncDecSetting.INC)
                m.d.comb += self.controls.writeRegister16.eq(Register16.PC)
                m.d.comb += self.controls.readRegister8.eq(
                    Register8.MCYCLER_RDATA)
                m.d.comb += self.controls.writeRegister8.eq(self.memrd_dest)
                self.execute(m)

                if self.include_z80fi:
                    m.d.comb += self.z80fi.control.add_operand.eq(1)
                    m.d.comb += self.z80fi.control.data.eq(self.z80fi.bus.data)
                    m.d.comb += self.z80fi.control.addr.eq(self.z80fi.bus.addr)
                    m.d.comb += self.z80fi.control.add_tcycle.eq(1)

            with m.State("RDMEM_T1"):
                m.d.comb += self.controls.readRegister16.eq(self.memrd_addr)
                m.d.comb += self.controls.readRegister8.eq(
                    Register8.MCYCLER_RDATA)
                if self.include_z80fi:
                    m.d.comb += self.z80fi.control.add_mcycle.eq(MCycle.MEMRD)
                m.next = "RDMEM_T2"

            # This state can be waitstated. If waitstated, self.act will be 0.
            with m.State("RDMEM_T2"):
                m.d.comb += self.controls.readRegister16.eq(self.memrd_addr)
                m.d.comb += self.controls.readRegister8.eq(
                    Register8.MCYCLER_RDATA)
                with m.If(self.act):
                    if self.include_z80fi:
                        m.d.comb += self.z80fi.control.add_tcycle.eq(1)
                    m.next = "RDMEM_T3"

            with m.State("RDMEM_T3"):
                m.d.comb += self.controls.readRegister16.eq(self.memrd_addr)
                m.d.comb += self.controls.readRegister8.eq(
                    Register8.MCYCLER_RDATA)
                m.d.comb += self.controls.writeRegister8.eq(self.memrd_dest)
                self.execute(m)

                if self.include_z80fi:
                    m.d.comb += self.z80fi.control.add_memrd_access.eq(1)
                    m.d.comb += self.z80fi.control.data.eq(self.z80fi.bus.data)
                    m.d.comb += self.z80fi.control.addr.eq(self.z80fi.bus.addr)
                    m.d.comb += self.z80fi.control.add_tcycle.eq(1)

            with m.State("WRMEM_T1"):
                m.d.comb += self.controls.readRegister16.eq(self.memwr_addr)
                m.d.comb += self.controls.readRegister8.eq(self.memwr_src)
                if self.include_z80fi:
                    m.d.comb += self.z80fi.control.add_mcycle.eq(MCycle.MEMWR)
                m.next = "WRMEM_T2"

            # This state can be waitstated. If waitstated, self.act will be 0.
            with m.State("WRMEM_T2"):
                m.d.comb += self.controls.readRegister16.eq(self.memwr_addr)
                m.d.comb += self.controls.readRegister8.eq(self.memwr_src)
                with m.If(self.act):
                    if self.include_z80fi:
                        m.d.comb += self.z80fi.control.add_tcycle.eq(1)
                    m.next = "WRMEM_T3"

            with m.State("WRMEM_T3"):
                m.d.comb += self.controls.readRegister16.eq(self.memwr_addr)
                m.d.comb += self.controls.readRegister8.eq(self.memwr_src)
                self.execute(m)

                if self.include_z80fi:
                    m.d.comb += self.z80fi.control.add_memwr_access.eq(1)
                    m.d.comb += self.z80fi.control.data.eq(self.z80fi.bus.data)
                    m.d.comb += self.z80fi.control.addr.eq(self.z80fi.bus.addr)
                    m.d.comb += self.z80fi.control.add_tcycle.eq(1)

            with m.State("HALT"):
                m.next = "HALT"

        return m

    def initiateInstructionFetch(self, m):
        """Initiates an M1 cycle for the first byte in an instruction.

        This resets any setting from prefixes and resets the cycle number.
        """
        self.initiateOpcodeFetch(m)
        m.d.pos += self.useIX.eq(0)
        m.d.pos += self.useIY.eq(0)
        m.d.pos += self.instr.en.eq(1)
        m.d.pos += self.cycle_num.eq(0)

    def initiateOpcodeFetch(self, m):
        """Initiates an M1 cycle for the first byte in an opcode.

        Differs from initiateInstructionFetch() in that it retains
        prefix settings and cycle numbers.

        * Registers (PC) -> addr bus (MCycler always gets this)
        * Enable INSTR.
        * PC is automatically incremented by state machine
        """
        m.next = "M1_T1"
        m.d.comb += self.cycle.eq(MCycle.M1)
        m.d.pos += self.instr.en.eq(1)

    def initiateOperandRead(self, m):
        """Initiates a memory read of an instruction operand.

        * Registers (PC) -> addr bus (MCycler always gets this)
        * Disable INSTR.
        * Instruction decides where data bus goes once read is done.
        * PC is automatically incremented by state machine
        """
        m.next = "RDOPERAND_T1"
        m.d.comb += self.cycle.eq(MCycle.MEMRD)
        m.d.pos += self.instr.en.eq(0)

    def initiateOperandReadInto(self, m, reg):
        """Initiates a memory read of an instruction operand into reg.

        * Registers (PC) -> addr bus (MCycler always gets this)
        * Disable INSTR.
        * Data goes into reg when done.
        * PC is automatically incremented by state machine
        """
        m.next = "RDOPERAND_T1"
        m.d.comb += self.cycle.eq(MCycle.MEMRD)
        m.d.pos += self.instr.en.eq(0)
        m.d.pos += self.memrd_dest.eq(reg)

    def initiateMemRead(self, m, reg_addr, reg_data):
        """Initiates a memory read using a 16-bit register as address.

        * Registers (reg) -> addr bus (MCycler always gets this)
        * Disable INSTR.
        * Instruction decides where data bus goes once read is done.
        """
        m.next = "RDMEM_T1"
        m.d.comb += self.cycle.eq(MCycle.MEMRD)
        m.d.pos += self.memrd_addr.eq(reg_addr)
        m.d.pos += self.memrd_dest.eq(reg_data)
        m.d.pos += self.instr.en.eq(0)

    def initiateMemWrite(self, m, reg_addr, reg_data):
        m.next = "WRMEM_T1"
        m.d.comb += self.cycle.eq(MCycle.MEMWR)
        m.d.pos += self.instr.en.eq(0)
        m.d.pos += self.memwr_addr.eq(reg_addr)
        m.d.pos += self.memwr_src.eq(reg_data)

    def aluAddrAddLow(self, m, reg16operand, reg_dest):
        self.extendCycle(m)
        m.d.pos += self.extended_cycle_controls.addrALUInput.eq(reg16operand)
        m.d.pos += self.extended_cycle_controls.addrALUInputByte.eq(0)
        m.d.pos += self.extended_cycle_controls.readRegister8.eq(
            Register8.ADDR_ALU)
        m.d.pos += self.extended_cycle_controls.writeRegister8.eq(reg_dest)

    def aluAddrAddHigh(self, m, reg16operand, reg_dest):
        self.extendCycle(m)
        m.d.pos += self.extended_cycle_controls.addrALUInput.eq(reg16operand)
        m.d.pos += self.extended_cycle_controls.addrALUInputByte.eq(1)
        m.d.pos += self.extended_cycle_controls.readRegister8.eq(
            Register8.ADDR_ALU)
        m.d.pos += self.extended_cycle_controls.writeRegister8.eq(reg_dest)

    def extendCycle(self, m):
        m.next = "EXTENDED"
        m.d.comb += self.extend.eq(1)
        m.d.pos += self.extended_cycle_controls.eq(0)
        m.d.pos += self.extended_cycle_controls.useIX.eq(self.useIX)
        m.d.pos += self.extended_cycle_controls.useIY.eq(self.useIY)
        m.d.pos += self.extended_cycle_controls.registerSet.eq(
            self.registerSet)

    def execute(self, m):
        m.d.pos += self.cycle_num.eq(self.cycle_num + 1)
        with m.Switch(self.instr.output):
            with m.Case(0xDD):
                m.d.pos += self.useIX.eq(1)
                m.d.pos += self.useIY.eq(0)
                m.d.pos += self.cycle_num.eq(0)
                self.initiateOpcodeFetch(m)

            with m.Case(0xFD):
                m.d.pos += self.useIX.eq(0)
                m.d.pos += self.useIY.eq(1)
                m.d.pos += self.cycle_num.eq(0)
                self.initiateOpcodeFetch(m)

            with m.Case("00000000"):
                self.NOP(m)

            with m.Case("01------"):
                self.LD_REG_REG(m)

            with m.Case("00---110"):
                self.LD_REG_N(m)

    def NOP(self, m):
        self.initiateInstructionFetch(m)

    def LD_REG_REG(self, m):
        dst_r = self.instr.output[3:6]
        src_r = self.instr.output[0:3]
        dst_hl = (dst_r == 6)
        src_hl = (src_r == 6)

        with m.If(self.cycle_num == 0):
            with m.If(dst_hl & src_hl):
                m.next = "HALT"
            with m.Elif(~dst_hl & ~src_hl):
                m.d.comb += self.controls.readRegister8.eq(Register8.r(src_r))
                m.d.comb += self.controls.writeRegister8.eq(Register8.r(dst_r))
                self.initiateInstructionFetch(m)
            with m.Elif(src_hl):
                self.initiateMemRead(m, Register16.HL, Register8.r(dst_r))
            with m.Else():
                self.initiateMemWrite(m, Register16.HL, Register8.r(src_r))
        with m.If(self.cycle_num == 1):
            with m.If(src_hl):
                m.d.comb += self.controls.writeRegister8.eq(Register8.r(dst_r))
            with m.Else():
                m.d.comb += self.controls.readRegister8.eq(Register8.r(src_r))
            self.initiateInstructionFetch(m)

    def LD_REG_N(self, m):
        r = self.instr.output[3:6]

        with m.If(r != 6):
            with m.If(self.cycle_num == 0):
                self.initiateOperandReadInto(m, Register8.r(r))
            with m.Else():
                self.initiateInstructionFetch(m)

        with m.Elif(~self.controls.useIX & ~self.controls.useIY):
            with m.If(self.cycle_num == 0):
                self.initiateOperandReadInto(m, Register8.TMP)
            with m.Elif(self.cycle_num == 1):
                self.initiateMemWrite(m, Register16.HL, Register8.TMP)
            with m.Else():
                self.initiateInstructionFetch(m)

        with m.Else():
            with m.If(self.cycle_num == 0):
                self.initiateOperandReadInto(m, Register8.OFFSET)
            with m.Elif(self.cycle_num == 1):
                self.initiateOperandReadInto(m, Register8.TMP)
            with m.Elif(self.cycle_num == 2):
                self.aluAddrAddLow(m, Register16.HL, Register8.Z)
            with m.Elif(self.cycle_num == 3):
                self.aluAddrAddHigh(m, Register16.HL, Register8.W)
            with m.Elif(self.cycle_num == 4):
                self.initiateMemWrite(m, Register16.WZ, Register8.TMP)
            with m.Else():
                self.initiateInstructionFetch(m)


if __name__ == "__main__":
    clk = Signal()
    rst = Signal()

    pos = ClockDomain()
    pos.clk = clk
    pos.rst = rst

    sequencer = Sequencer()

    m = Module()
    m.domains.pos = pos
    m.submodules.sequencer = sequencer

    main(m, ports=[clk, rst] + sequencer.ports(), platform="formal")
