module capture_controller (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        arm,
    input  wire        spi_valid,
    input  wire        spi_stop,
    input  wire [7:0]  spi_mosi,
    input  wire [7:0]  spi_miso,
    output reg  [6:0]  wr_addr,
    output reg  [15:0] wr_data,
    output reg         we,
    output reg         capture_done,
    output reg  [6:0]  capture_length
);
    reg active;
    reg [6:0] byte_count;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_addr        <= 7'd0;
            we             <= 1'b0;
            capture_done   <= 1'b0;
            active         <= 1'b0;
            wr_data        <= 16'd0;
            capture_length <= 7'd0;
            byte_count     <= 7'd0;
        end else begin
            we <= 1'b0; 
            
            if (arm) begin
                active         <= 1'b1;
                capture_done   <= 1'b0;
                capture_length <= 7'd0;
                byte_count     <= 7'd0;
            end else if (active) begin
                
                if (spi_valid && byte_count < 7'd64) begin
                    wr_data    <= {spi_mosi, spi_miso};
                    wr_addr    <= byte_count; 
                    we         <= 1'b1;       
                    byte_count <= byte_count + 7'd1; 
                end
                
                if (spi_stop) begin
                    active       <= 1'b0;
                    capture_done <= 1'b1;
                    
                    if (spi_valid && byte_count < 7'd64) begin
                        capture_length <= byte_count + 7'd1;
                    end else begin
                        capture_length <= byte_count;
                    end
                end
                
            end
        end
    end
endmodule