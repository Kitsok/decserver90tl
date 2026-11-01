-- Project-owned standalone target; no upstream C++ changes are required.
STANDALONE = true

CPUS["M680X0"] = true
MACHINES["AM79C90"] = true
MACHINES["68681"] = true

function standalone()
    -- Keep outputs distinct when switching frontend modes in one checkout.
    targetname "ds90tl-standalone"
    files {
        MAME_DIR .. "src/ds90tl/ds90tl.cpp",
        MAME_DIR .. "src/mame/dec/decserver90tl.cpp",
        MAME_DIR .. "src/mame/dec/decserver90tl_nvram.h",
    }
end
