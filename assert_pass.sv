module passme(
    input logic clk,
    input logic rst
);

reg [7:0] cycle = 0;

always @(posedge clk) begin
    cycle <= cycle + (cycle != 255);
end

always @(*) begin
    assume(rst == cycle < 2);
    if (!rst) assert(cycle == 0);
end

endmodule

module top(
    input logic clk,
    input logic rst
);

passme passme(
    .clk(clk),
    .rst(rst)
);

endmodule
