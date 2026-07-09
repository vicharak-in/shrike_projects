module spi_decoder (
    input  wire       clk,
    input  wire       rst_n,
    
    input  wire       spi_mon_cs_n,
    input  wire       spi_mon_sclk,
    input  wire       spi_mon_mosi,
    input  wire       spi_mon_miso,
    
    output reg        pkt_valid,
    output reg        pkt_start,
    output reg        pkt_stop,
    output reg  [7:0] pkt_mosi,
    output reg  [7:0] pkt_miso
);

    
    reg [3:0] cs_filter;
    reg [2:0] sclk_sync;
    reg [1:0] mosi_sync;
    reg [1:0] miso_sync;
    
    reg cs_clean;
    reg cs_clean_d;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cs_filter  <= 4'b1111;
            cs_clean   <= 1'b1;
            cs_clean_d <= 1'b1;
            sclk_sync  <= 3'b000;
            mosi_sync  <= 2'b00;
            miso_sync  <= 2'b00;
        end else begin
    
            cs_filter <= {cs_filter[2:0], spi_mon_cs_n};
            
            
            if (cs_filter[3:1] == 3'b111) cs_clean <= 1'b1;
            else if (cs_filter[3:1] == 3'b000) cs_clean <= 1'b0;
            
            cs_clean_d <= cs_clean;
            
            sclk_sync <= {sclk_sync[1:0], spi_mon_sclk};
            mosi_sync <= {mosi_sync[0], spi_mon_mosi};
            miso_sync <= {miso_sync[0], spi_mon_miso};
        end
    end

    wire cs_fall   = (cs_clean_d == 1'b1 && cs_clean == 1'b0);
    wire cs_rise   = (cs_clean_d == 1'b0 && cs_clean == 1'b1);
    wire sclk_rise = (sclk_sync[2:1] == 2'b01); 

    // ── Decoder
    reg       active;
    reg [2:0] bit_cnt;
    reg       byte_seen;
    reg       first_byte;
    reg [7:0] mosi_shift;
    reg [7:0] miso_shift;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active     <= 1'b0;
            bit_cnt    <= 3'd0;
            byte_seen  <= 1'b0;
            first_byte <= 1'b0;
            mosi_shift <= 8'd0;
            miso_shift <= 8'd0;
            
            pkt_start  <= 1'b0;
            pkt_stop   <= 1'b0;
            pkt_valid  <= 1'b0;
            pkt_mosi   <= 8'd0;
            pkt_miso   <= 8'd0;
        end else begin
            pkt_start <= 1'b0;
            pkt_stop  <= 1'b0;
            pkt_valid <= 1'b0;

            if (cs_fall) begin
                active     <= 1'b1;
                bit_cnt    <= 3'd0;
                byte_seen  <= 1'b0;
                first_byte <= 1'b1;
                mosi_shift <= 8'd0;
                miso_shift <= 8'd0;
            end 
            else if (cs_rise) begin
                active <= 1'b0;
                if (byte_seen) begin
                    pkt_stop <= 1'b1;
                end
            end 
            else if (active && sclk_rise) begin
                mosi_shift <= {mosi_shift[6:0], mosi_sync[1]};
                miso_shift <= {miso_shift[6:0], miso_sync[1]};
                
                if (bit_cnt == 3'd7) begin
                    bit_cnt   <= 3'd0;
                    pkt_mosi  <= {mosi_shift[6:0], mosi_sync[1]};
                    pkt_miso  <= {miso_shift[6:0], miso_sync[1]};
                    pkt_valid <= 1'b1;
                    byte_seen <= 1'b1;

                    if (first_byte) begin
                        pkt_start  <= 1'b1;
                        first_byte <= 1'b0;
                    end
                end else begin
                    bit_cnt <= bit_cnt + 3'd1;
                end
            end
        end
    end
endmodule