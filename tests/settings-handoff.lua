-- Observe firmware validation, rather than manufacturing success in the test.
local memory = manager.machine.devices[":maincpu"].spaces["program"]
local flags = memory:read_u32(0x7805016)
assert((flags & 0x380000) == 0, "Factory fallback must not be forced")
local fallback = (flags & 0x40000) ~= 0
assert(fallback == (os.getenv("DS90_EXPECT_SERVER_FALLBACK") == "1"), "Server checksum validation changed")
if os.getenv("DS90_CUSTOM_FACTORY") == "1" then
    local value = ""
    for index = 1, 6 do value = value .. string.char(memory:read_u8(0x100c1e + index)) end
    assert(value == "CUSTOM", "Existing factory field overwritten")
    value = ""
    for index = 1, 6 do value = value .. string.char(memory:read_u8(0x79ac5d2 + index)) end
    assert(value == "CUSTOM", "Factory field not loaded by firmware")
else
    for _, field in ipairs({{0x08,0x786c264,14},{0x1e,0x786c272,20},{0x32,0x786c286,8}}) do
        for index = 0, field[3] - 1 do
            assert(memory:read_u8(0x100c00 + field[1] + index) == memory:read_u8(field[2] + index), "Factory defaults mismatch")
        end
    end
end
print(string.format("DS90 SETTINGS-HANDOFF-PASS flags=%08x server_fallback=%s", flags, tostring(fallback)))
