module spi_capture_bram (
    input  wire        clk,
    input  wire        we,
    input  wire [6:0]  wr_addr,
    input  wire [15:0] wr_data,
    input  wire [6:0]  rd_addr,
    output reg  [15:0] rd_data
);
    
    reg [15:0] ram [0:63];

    always @(posedge clk) begin
        if (we) begin
            ram[wr_addr] <= wr_data;
        end
        rd_data <= ram[rd_addr];
    end
endmodule