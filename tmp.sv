module z80fi_insn_spec_ld_reg_n(
    input logic [7:0] z80fi_insn,
    output logic spec_valid
);

assign spec_valid = z80fi_insn[7:0] == 8'b00???110;

endmodule