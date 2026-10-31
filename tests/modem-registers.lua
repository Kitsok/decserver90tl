-- Isolated component test only: stop guest execution in a private RAM loop,
-- then drive the board's UART registers through the CPU address space.
local cpu = manager.machine.devices[":maincpu"]
local memory = cpu.spaces["program"]
local directory = assert(os.getenv("DS90_MODEM_TEST_DIR"))
memory:write_u16(0xbfff00, 0x60fe)
cpu.state["SR"].value = 0x2700
cpu.state["PC"].value = 0xbfff00
local function base(port) return 0x400000 + (port - 1) * 0x10 end
for port = 1, 8 do
    local address = base(port)
    memory:write_u8(address + 4, 0x20)
    memory:write_u8(address + 4, 0x30)
    memory:write_u8(address + 4, 0x10)
    memory:write_u8(address, 0x93) -- eight bits; automatic receive RTS/DTR
    memory:write_u8(address, 0x17) -- CTS/DSR-controlled TX
    memory:write_u8(address + 2, 0xcc)
    memory:write_u8(address + 4, 0x05)
    memory:write_u8(address + 4, 0x80)
end
local function marker(name)
    local file = assert(io.open(directory .. "/" .. name, "w"))
    file:write("ready\n")
    file:close()
end
local stage = 1
marker("ready")
local actions = {
    { "transmit", function()
        for port = 1, 8 do memory:write_u8(base(port) + 6, 64 + port) end
    end },
    { "dtr-low", function()
        for port = 1, 8 do memory:write_u8(base(port) + 4, 0x90) end
    end },
    { "dtr-high", function()
        for port = 1, 8 do memory:write_u8(base(port) + 4, 0x80) end
    end },
    { "receive-drain", function()
        for port = 1, 8 do assert(memory:read_u8(base(port) + 6) == 97) end
    end },
    { "reset-receivers", function()
        for port = 1, 8 do memory:write_u8(base(port) + 4, 0x20) end
    end },
    { "ignore-dsr", function()
        for port = 1, 8 do
            memory:write_u8(base(port) + 4, 0x10)
            memory:write_u8(base(port), 0x13)
            memory:write_u8(base(port), 0x07)
            memory:write_u8(base(port) + 6, 96 + port)
        end
    end },
    { "hold-reset", function()
        for port = 1, 8 do
            memory:write_u8(base(port) + 4, 0x10)
            memory:write_u8(base(port), 0x13)
            memory:write_u8(base(port), 0x17)
            memory:write_u8(base(port) + 6, 48 + port)
        end
    end },
    { "reset-transmitters", function()
        for port = 1, 8 do memory:write_u8(base(port) + 4, 0x30) end
    end }
}
emu.register_periodic(function()
    local action = actions[stage]
    if not action then return end
    local file = io.open(directory .. "/" .. action[1], "r")
    if not file then return end
    file:close()
    action[2]()
    marker(action[1] .. "-done")
    stage = stage + 1
end)
