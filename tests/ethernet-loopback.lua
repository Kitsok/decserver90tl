-- Component fixture: hold the CPU in a private RAM loop, then use its bus
-- to exercise the real AM7990 initialization, DMA rings, RX/TX and interrupts.
local cpu = manager.machine.devices[":maincpu"]
local memory = cpu.spaces["program"]
memory:write_u16(0xbfff00, 0x60fe)
cpu.state["SR"].value = 0x2700
cpu.state["PC"].value = 0xbfff00
local function csr(index, value)
    memory:write_u16(0x300002, index)
    if value ~= nil then memory:write_u16(0x300000, value) end
    return memory:read_u16(0x300000)
end
csr(0, 4)
local init, rxring, txring, rxbuf, txbuf = 0xbfe000, 0xbfe100, 0xbfe108, 0xbfd000, 0xbfd800
local words = {0x44, 0x9002, 0, 0x0100, 0, 0, 0, 0, 0xe100, 0xbf, 0xe108, 0xbf}
for index, word in ipairs(words) do memory:write_u16(init + (index - 1) * 2, word) end
memory:write_u16(rxring, 0xd000)
memory:write_u16(rxring + 2, 0x80bf)
memory:write_u16(rxring + 4, 0xfa00)
memory:write_u16(rxring + 6, 0)
local frame = {255,255,255,255,255,255,2,0x90,0,0,0,1,0x88,0xb5}
for index = 15, 32 do frame[index] = index - 15 end
for index, byte in ipairs(frame) do memory:write_u8(txbuf + index - 1, byte) end
memory:write_u16(txring, 0xd800)
memory:write_u16(txring + 2, 0x83bf)
memory:write_u16(txring + 4, 0xffe0)
memory:write_u16(txring + 6, 0)
csr(1, init & 0xffff)
csr(2, init >> 16)
csr(3, 6)
assert((csr(0, 0x41) & 0x100) ~= 0, "LANCE initialization failed")
csr(0, 0x142)
csr(0, 0x48)
local complete = false
emu.register_periodic(function()
    if complete or (memory:read_u16(rxring + 2) & 0x8000) ~= 0 then return end
    assert((memory:read_u16(txring + 2) & 0xc000) == 0, "TX ownership/error")
    assert((memory:read_u16(rxring + 2) & 0xc300) == 0x0300, "RX status")
    assert(memory:read_u16(rxring + 6) == 36, "RX length including FCS")
    for index, byte in ipairs(frame) do
        assert(memory:read_u8(rxbuf + index - 1) == byte, "DMA byte ordering")
    end
    assert((csr(0) & 0x680) == 0x680, "RX/TX pending interrupt flags")
    csr(0, 0x640)
    assert((csr(0) & 0x680) == 0, "Interrupt acknowledgement failed")
    complete = true
    print("DS90 ETHERNET-LOOPBACK-PASS bytes=32 received=36 csr3=6 dma=24bit irq=rx+tx+ack")
end)
