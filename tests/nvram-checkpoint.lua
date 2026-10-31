-- Component fixture: stop guest execution, then independently exercise queue
-- gating and memory-device writes in unused backing bytes. No CLI hooks.
local cpu = manager.machine.devices[":maincpu"]
local memory = cpu.spaces["program"]
local directory = assert(os.getenv("DS90_NVRAM_TEST_DIR"))
memory:write_u16(0xbfff00, 0x60fe)
cpu.state["SR"].value = 0x2700
cpu.state["PC"].value = 0xbfff00
memory:write_u32(0x798fb20, 0)
memory:write_u8(0x798fa86, 0)
local function marker(name)
    local file = assert(io.open(directory .. "/" .. name, "w"))
    file:write("done\n")
    file:close()
end
marker("ready")
local stages = {
    {"flag-pending", function()
        memory:write_u8(0x798fa86, 1)
        memory:write_u8(0x10ff00, 0x12)
    end},
    {"head-pending", function()
        memory:write_u8(0x798fa86, 0)
        memory:write_u32(0x798fb20, 0x98fb20)
        memory:write_u8(0x10ff00, 0x34)
    end},
    {"queue-idle", function()
        memory:write_u32(0x798fb20, 0)
    end},
    {"exit-pending", function()
        memory:write_u8(0x798fa86, 1)
        memory:write_u8(0x10ff00, 0x56)
        manager.machine:exit()
    end}
}
local next_stage = 1
emu.register_periodic(function()
    local action = stages[next_stage]
    if not action then return end
    local file = io.open(directory .. "/" .. action[1], "r")
    if not file then return end
    file:close()
    action[2]()
    marker(action[1] .. "-done")
    next_stage = next_stage + 1
end)
