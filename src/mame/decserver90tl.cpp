// SPDX-License-Identifier: BSD-3-Clause
// Experimental MNENG3 / 4 MiB bring-up. No boot ROM or host firmware patches.
#include "emu.h"
#include "cpu/m68000/fscpu32.h"
#include "machine/am79c90.h"
#include "machine/mc68681.h"

#include <algorithm>
#include <cstdio>

class ds90_cpu_device : public fscpu32_device
{
public:
	ds90_cpu_device(const machine_config &config, const char *tag, device_t *owner, u32 clock);
};
DECLARE_DEVICE_TYPE(DS90_CPU, ds90_cpu_device)
DEFINE_DEVICE_TYPE(DS90_CPU, ds90_cpu_device, "ds90cpu", "DECserver CPU32 bring-up")
ds90_cpu_device::ds90_cpu_device(const machine_config &config, const char *tag, device_t *owner, u32 clock)
	: fscpu32_device(config, tag, owner, clock, DS90_CPU, address_map_constructor())
{ }

namespace {

class ds90tl_state : public driver_device
{
public:
	ds90tl_state(const machine_config &config, device_type type, const char *tag)
		: driver_device(config, type, tag), m_cpu(*this, "maincpu"),
		  m_lance(*this, "lance"), m_uart(*this, "uart%u", 0U), m_ram(*this, "ram")
	{ }
	void ds90tl(machine_config &config);

protected:
	void machine_start() override;
	void machine_reset() override;

private:
	void memory_map(address_map &map);
	u16 boot_r(offs_t offset) { return m_boot[offset]; }
	u16 unexpected_r(offs_t offset, u16 mask = ~0);
	void unexpected_w(offs_t offset, u16 data, u16 mask = ~0);
	u16 peripheral_r(offs_t offset, u16 mask = ~0);
	void peripheral_w(offs_t offset, u16 data, u16 mask = ~0);
	template<unsigned Block> u16 uart_r(offs_t offset, u16 mask = ~0);
	template<unsigned Block> void uart_w(offs_t offset, u16 data, u16 mask = ~0);
	u16 dma_r(offs_t offset);
	void dma_w(offs_t offset, u16 data, u16 mask = ~0);
	void lance_irq(int state);
	void record(const char *kind, u32 address, u16 data, u16 mask);
	void dump_state();
	TIMER_CALLBACK_MEMBER(observe);
	TIMER_CALLBACK_MEMBER(tpu_complete);
	required_device<ds90_cpu_device> m_cpu;
	required_device<am7990_device> m_lance;
	required_device_array<mc68681_device, 4> m_uart;
	required_shared_ptr<u16> m_ram;
	u16 m_boot[0x1000]{};
	u16 m_peripheral[0x300]{}; // FFFA00..FFFFFF, includes TPU parameter RAM
	u32 m_events = 0;
	u32 m_ticks = 0;
	emu_timer *m_observer = nullptr;
	emu_timer *m_tpu_timer = nullptr;
};

void ds90tl_state::dump_state()
{
	std::fprintf(stderr, "DS90 STATE pc=%08x sp=%08x vbr=%08x sr=%04x\n",
		u32(m_cpu->pc()), u32(m_cpu->state_int(M68K_SP)),
		u32(m_cpu->state_int(M68K_VBR)), u16(m_cpu->state_int(M68K_SR)));
	for (unsigned i = 0; i < 8; ++i)
		std::fprintf(stderr, "DS90 STATE d%u=%08x a%u=%08x\n", i,
			u32(m_cpu->state_int(M68K_D0 + i)), i, u32(m_cpu->state_int(M68K_A0 + i)));
}

void ds90tl_state::record(const char *kind, u32 address, u16 data, u16 mask)
{
	if (machine().side_effects_disabled()) return;
	if (m_events++ < 300)
		std::fprintf(stderr, "DS90 %s pc=%08x address=%06x data=%04x mask=%04x\n",
			kind, u32(m_cpu->pc()), address, data, mask);
}

u16 ds90tl_state::unexpected_r(offs_t offset, u16 mask)
{
	if (!machine().side_effects_disabled())
	{
		dump_state();
		fatalerror("DS90 unsupported read pc=%08x address=%06x mask=%04x\n",
			u32(m_cpu->pc()), u32(offset * 2), mask);
	}
	return 0xffff;
}

void ds90tl_state::unexpected_w(offs_t offset, u16 data, u16 mask)
{
	dump_state();
	fatalerror("DS90 unsupported write pc=%08x address=%06x data=%04x mask=%04x\n",
		u32(m_cpu->pc()), u32(offset * 2), data, mask);
}

u16 ds90tl_state::peripheral_r(offs_t offset, u16 mask)
{
	const u32 address = 0xfffa00 + offset * 2;
	u16 value = m_peripheral[offset];
	// Reset-status register: a synthetic cold power-on, not captured ROM state.
	if (address == 0xfffa06) value = 0x0080;
	record("READ-INTERNAL", address, value, mask);
	return value;
}

void ds90tl_state::peripheral_w(offs_t offset, u16 data, u16 mask)
{
	const u32 address = 0xfffa00 + offset * 2;
	record("WRITE-INTERNAL", address, data, mask);
	m_peripheral[offset] = (m_peripheral[offset] & ~mask) | (data & mask);
	if (address == 0xfffe18 || address == 0xfffe1a)
		m_tpu_timer->adjust(attotime::from_usec(2));
}

TIMER_CALLBACK_MEMBER(ds90tl_state::tpu_complete)
{
	// Explicit provisional bootstrap substitution: complete requests only.
	// No claim that TPU function/parameter side effects are implemented yet.
	m_peripheral[(0xfffe18 - 0xfffa00) / 2] = 0;
	m_peripheral[(0xfffe1a - 0xfffa00) / 2] = 0;
}

template<unsigned Block> u16 ds90tl_state::uart_r(offs_t offset, u16 mask)
{
	const u8 value = m_uart[Block]->read(offset);
	record("READ-UART", 0x400000 + Block * 0x20 + offset * 2, value, mask);
	return u16(value) << 8; // guest uses byte registers at even addresses
}

template<unsigned Block> void ds90tl_state::uart_w(offs_t offset, u16 data, u16 mask)
{
	record("WRITE-UART", 0x400000 + Block * 0x20 + offset * 2, data, mask);
	if (mask & 0xff00)
	{
		const u8 value = data >> 8;
		if (offset == 3 || offset == 11)
			std::fprintf(stderr, "DS90 UART-TX port=%u byte=%02x char=%c\n",
				Block * 2 + (offset == 11) + 1, value, value >= 32 && value < 127 ? value : '.');
		m_uart[Block]->write(offset, value);
	}
}

u16 ds90tl_state::dma_r(offs_t offset)
{
	// MAME LANCE supplies a byte address and expects a numeric 16-bit word.
	return m_cpu->space(AS_PROGRAM).read_word(offset & 0xffffff);
}

void ds90tl_state::dma_w(offs_t offset, u16 data, u16 mask)
{
	m_cpu->space(AS_PROGRAM).write_word(offset & 0xffffff, data, mask);
}

void ds90tl_state::lance_irq(int state)
{
	// MAME LANCE's callback is active-low.
	m_cpu->set_input_line(3, state ? CLEAR_LINE : ASSERT_LINE);
}

void ds90tl_state::memory_map(address_map &map)
{
	map.global_mask(0x00ffffff); // provisional 24-bit external decode
	map(0x000000, 0xffffff).rw(FUNC(ds90tl_state::unexpected_r), FUNC(ds90tl_state::unexpected_w));
	map(0x000000, 0x001fff).r(FUNC(ds90tl_state::boot_r));
	map(0x300000, 0x300003).rw(m_lance, FUNC(am7990_device::regs_r), FUNC(am7990_device::regs_w));
	map(0x400000, 0x40001f).rw(FUNC(ds90tl_state::uart_r<0>), FUNC(ds90tl_state::uart_w<0>));
	map(0x400020, 0x40003f).rw(FUNC(ds90tl_state::uart_r<1>), FUNC(ds90tl_state::uart_w<1>));
	map(0x400040, 0x40005f).rw(FUNC(ds90tl_state::uart_r<2>), FUNC(ds90tl_state::uart_w<2>));
	map(0x400060, 0x40007f).rw(FUNC(ds90tl_state::uart_r<3>), FUNC(ds90tl_state::uart_w<3>));
	map(0x800000, 0xbfffff).ram().share("ram");
	map(0xfff000, 0xfff7ff).ram();
	map(0xfffa00, 0xffffff).rw(FUNC(ds90tl_state::peripheral_r), FUNC(ds90tl_state::peripheral_w));
}

void ds90tl_state::machine_start()
{
	m_observer = timer_alloc(FUNC(ds90tl_state::observe), this);
	m_tpu_timer = timer_alloc(FUNC(ds90tl_state::tpu_complete), this);
}

void ds90tl_state::machine_reset()
{
	auto &space = m_cpu->space(AS_PROGRAM);
	std::fill_n(&m_ram[0], 0x400000 / 2, 0);
	std::fill(std::begin(m_peripheral), std::end(m_peripheral), 0);
	std::fill(std::begin(m_boot), std::end(m_boot), 0);
	// All inherited exception vectors stop at a distinct synthetic sentinel.
	for (unsigned vector = 2; vector < 256; ++vector)
	{
		const u32 destination = 0x1000 + vector * 4;
		m_boot[vector * 2] = destination >> 16;
		m_boot[vector * 2 + 1] = destination;
		m_boot[destination / 2] = 0x60fe; // BRA to self, reported by observer
	}
	m_boot[0] = 0x07bf; m_boot[1] = 0xf000; // inherited SP
	m_boot[2] = 0x0787; m_boot[3] = 0x13f8; // MNENG3 startup, bypass debugger
	const auto *image = memregion("firmware")->base();
	for (unsigned i = 0; i < memregion("firmware")->bytes(); ++i)
		space.write_byte(0x805000 + i, image[i]);
	// Handoff memory-size field consumed by 0x07940578.
	space.write_dword(0x8051b6, 0x400000);
	m_events = m_ticks = 0;
	std::fprintf(stderr, "DS90 BOOT image=MNENG3 ram=4194304 entry=078713f8 sp=07bff000 vbr=0\n"
		"DS90 EXPERIMENTAL handoff: synthetic vectors/RAM-size; TPU completion substitution; no network backend\n");
	m_observer->adjust(attotime::from_msec(1), 0, attotime::from_msec(1));
}

TIMER_CALLBACK_MEMBER(ds90tl_state::observe)
{
	const u32 pc = m_cpu->pc();
	const u32 sp = m_cpu->state_int(M68K_SP);
	if (pc >= 0x1000 && pc < 0x1400)
		fatalerror("DS90 inherited exception vector=%u pc=%08x sp=%08x saved_pc=%08x\n",
			(pc - 0x1000) / 4, pc, sp, m_cpu->space(AS_PROGRAM).read_dword(sp + 2));
	if (++m_ticks <= 10 || m_ticks % 100 == 0)
		std::fprintf(stderr, "DS90 PROGRESS ms=%u pc=%08x sp=%08x sr=%04x\n",
			m_ticks, pc, sp, u16(m_cpu->state_int(M68K_SR)));
}

void ds90tl_state::ds90tl(machine_config &config)
{
	DS90_CPU(config, m_cpu, 16'000'000); // provisional clock, not measured
	m_cpu->set_addrmap(AS_PROGRAM, &ds90tl_state::memory_map);
	AM7990(config, m_lance, 20'000'000);
	m_lance->dma_in().set(FUNC(ds90tl_state::dma_r));
	m_lance->dma_out().set(FUNC(ds90tl_state::dma_w));
	m_lance->intr_out().set(FUNC(ds90tl_state::lance_irq));
	for (unsigned i = 0; i < 4; ++i)
		MC68681(config, m_uart[i], 3'686'400); // clock/variant still provisional
}

static INPUT_PORTS_START(ds90tl)
INPUT_PORTS_END

ROM_START(ds90tl)
	ROM_REGION(0x18b600, "firmware", 0)
	ROM_LOAD("MNENG3.SYS", 0, 0x18b600, CRC(5275e52d) SHA1(df36a007dd3da3b6dbacf96318787e5e07d7f378))
ROM_END

} // anonymous namespace

COMP(1992, ds90tl, 0, 0, ds90tl, ds90tl, ds90tl_state, empty_init,
	"Digital Equipment Corporation", "DECserver 90TL (MNENG3 bring-up)", MACHINE_NOT_WORKING | MACHINE_NO_SOUND_HW)
