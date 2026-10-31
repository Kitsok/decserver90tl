// SPDX-License-Identifier: BSD-3-Clause
// Experimental MNENG3 / 4 MiB bring-up. No boot ROM or host firmware patches.
#include "emu.h"
#include "cpu/m68000/fscpu32.h"
#include "machine/am79c90.h"
#include "machine/mc68681.h"
#include "machine/nvram.h"

#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <deque>
#include <cerrno>
#include <csignal>
#include <fcntl.h>
#include <termios.h>
#include <unistd.h>

class ds90_cpu_device : public fscpu32_device
{
public:
	ds90_cpu_device(const machine_config &config, const char *tag, device_t *owner, u32 clock);
protected:
	void device_start() override
	{
		fscpu32_device::device_start();
		const char *assist = std::getenv("DS90_ROM_ALIGNMENT_ASSIST");
		m_alignment_assist = assist && std::string_view(assist) == "1";
		const char *wait = std::getenv("DS90_RAM_WAIT_CYCLES");
		m_ram_wait_cycles = wait ? std::clamp(std::atoi(wait), 0, 16) : 0;
		std::fprintf(stderr, "DS90 CPU rom_alignment_assist=%u ram_wait_cycles=%u\n",
			unsigned(m_alignment_assist), m_ram_wait_cycles);
		auto immediate16 = m_readimm16;
		m_readimm16 = [this, immediate16](offs_t address) -> u16 {
			ram_wait(address, 1);
			return immediate16(address);
		};
		auto read8 = m_read8;
		m_read8 = [this, read8](offs_t address) -> u8 {
			ram_wait(address, 1);
			return read8(address);
		};
		auto read16 = m_read16;
		m_read16 = [this, read16](offs_t address) -> u16 {
			ram_wait(address, (address & 1) ? 2 : 1);
			if (alignment(address, "read16")) return m_program16.read_word_unaligned(address);
			return read16(address);
		};
		auto read32 = m_read32;
		m_read32 = [this, read32](offs_t address) -> u32 {
			ram_wait(address, (address & 1) ? 3 : 2);
			if (address == 0x079ab718 && u32(pc()) == 0x07941626)
			{
				const u32 remaining = state_int(M68K_D1);
				if (remaining == 0x707) m_idle_first_cycle = total_cycles();
				if (remaining == 1)
					std::fprintf(stderr, "DS90 IDLE-BUDGET cycles=%llu cpu_hz=%u elapsed_us=%.3f\n",
						static_cast<unsigned long long>(total_cycles() - m_idle_first_cycle), clock(),
						1e6 * double(total_cycles() - m_idle_first_cycle) / clock());
			}
			if (alignment(address, "read32")) return m_program16.read_dword_unaligned(address);
			return read32(address);
		};
		auto write16 = m_write16;
		m_write16 = [this, write16](offs_t address, u16 data) {
			ram_wait(address, (address & 1) ? 2 : 1);
			if (alignment(address, "write16")) m_program16.write_word_unaligned(address, data);
			else write16(address, data);
		};
		auto write32 = m_write32;
		m_write32 = [this, write32](offs_t address, u32 data) {
			ram_wait(address, (address & 1) ? 3 : 2);
			if (alignment(address, "write32")) m_program16.write_dword_unaligned(address, data);
			else write32(address, data);
		};
		auto write8 = m_write8;
		m_write8 = [this, write8](offs_t address, u8 data) {
			ram_wait(address, 1);
			write8(address, data);
		};
	}
private:
	void ram_wait(offs_t address, unsigned transfers)
	{
		const u32 physical = address & 0xffffff;
		if (physical >= 0x800000 && physical <= 0xbfffff)
			adjust_icount(-int(m_ram_wait_cycles * transfers));
	}
	bool alignment(offs_t address, const char *operation)
	{
		if (!(address & 1)) return false;
		if (!m_alignment_assist)
			fatalerror("DS90 unresolved CPU32 address error: %s pc=%08x address=%08x\n", operation, u32(pc()), u32(address));
		if (m_alignment_events++ < 16)
			std::fprintf(stderr, "DS90 ROM-ALIGNMENT-ASSIST %s pc=%08x address=%08x\n", operation, u32(pc()), u32(address));
		return true;
	}
	bool m_alignment_assist = false;
	u32 m_alignment_events = 0;
	u64 m_idle_first_cycle = 0;
	unsigned m_ram_wait_cycles = 0;
};
DECLARE_DEVICE_TYPE(DS90_CPU, ds90_cpu_device)
DEFINE_DEVICE_TYPE(DS90_CPU, ds90_cpu_device, "ds90cpu", "DECserver CPU32 bring-up")
ds90_cpu_device::ds90_cpu_device(const machine_config &config, const char *tag, device_t *owner, u32 clock)
	: fscpu32_device(config, tag, owner, clock, DS90_CPU, address_map_constructor())
{ }

namespace {

volatile std::sig_atomic_t serial_stop_requested = 0;
void serial_stop(int) { serial_stop_requested = 1; }

class ds90tl_state : public driver_device
{
public:
	ds90tl_state(const machine_config &config, device_type type, const char *tag)
		: driver_device(config, type, tag), m_cpu(*this, "maincpu"),
		  m_lance(*this, "lance"), m_uart(*this, "uart%u", 0U), m_ram(*this, "ram")
	{ }
	~ds90tl_state() override;
	void ds90tl(machine_config &config);

protected:
	void machine_start() override;
	void machine_reset() override;

private:
	void memory_map(address_map &map);
	u16 boot_r(offs_t offset) { return m_boot[offset]; }
	u16 identity_r(offs_t offset)
	{
		// Provisional board-clock acknowledge, inferred from the ISR's TST.B.
		if (offset == 0 && !machine().side_effects_disabled())
			m_cpu->set_input_line(6, CLEAR_LINE);
		// Synthetic locally administered Ethernet address 02:90:00:00:00:01.
		static constexpr u16 words[] = { 0x0290, 0x0000, 0x0001 };
		return words[offset];
	}
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
	TIMER_CALLBACK_MEMBER(clock_tick);
	TIMER_CALLBACK_MEMBER(uart_probe);
	TIMER_CALLBACK_MEMBER(serial_poll);
	int m_pty[8] = {-1,-1,-1,-1,-1,-1,-1,-1};
	int m_pty_slave[8] = {-1,-1,-1,-1,-1,-1,-1,-1};
	std::deque<u8> m_serial_output[8];
	emu_timer *m_serial_timer = nullptr;
	required_device<ds90_cpu_device> m_cpu;
	required_device<am7990_device> m_lance;
	required_device_array<mc68681_device, 4> m_uart;
	required_shared_ptr<u16> m_ram;
	u16 m_boot[0x1000]{};
	u16 m_peripheral[0x300]{}; // FFFA00..FFFFFF, includes TPU parameter RAM
	u32 m_events = 0;
	u32 m_ticks = 0;
	u32 m_clock_ticks = 0;
	unsigned m_probe_port = 0;
	unsigned m_probe_count = 0;
	std::vector<u8> m_probe_data;
	unsigned m_serial_events = 0;
	unsigned m_uart_commands[8]{};
	emu_timer *m_observer = nullptr;
	emu_timer *m_tpu_timer = nullptr;
	emu_timer *m_clock_timer = nullptr;
	emu_timer *m_probe_timer = nullptr;
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
	if (address == 0xfffe20)
	{
		// Functional substitution for the recovered TPU receive/DUART
		// status paths. Physical signal routing and edge latches are unknown.
		for (unsigned block = 0; block < 4; ++block)
		{
			if (m_uart[block]->m_chanA->read_chan_reg(1) & 1) value |= 1U << (block * 2);
			if (m_uart[block]->m_chanB->read_chan_reg(1) & 1) value |= 1U << (block * 2 + 1);
			if (m_uart[block]->irq_pending()) value |= 1U << (8 + block);
		}
		if (value && m_serial_events++ < 32)
			std::fprintf(stderr, "DS90 SERIAL-STATUS pc=%08x cisr=%04x\n", u32(m_cpu->pc()), value);
	}
	record("READ-INTERNAL", address, value, mask);
	return value;
}

void ds90tl_state::peripheral_w(offs_t offset, u16 data, u16 mask)
{
	const u32 address = 0xfffa00 + offset * 2;
	record("WRITE-INTERNAL", address, data, mask);
	if (address == 0xfffe20)
		m_peripheral[offset] &= data | ~mask; // CISR bits clear when zero is written
	else
		m_peripheral[offset] = (m_peripheral[offset] & ~mask) | (data & mask);
	if (address == 0xfffe18 || address == 0xfffe1a)
		m_tpu_timer->adjust(attotime::from_usec(2));
	if (address == 0xfffe1c)
	{
		// Channel 14 priority gates the recovered board-clock path. The
		// firmware ISR divides the incoming pulses by approximately 16 before
		// adding 1953 + fractional microseconds (512 guest ticks/second).
		// The 8192 Hz pulse rate is inferred, not measured from hardware.
		// This substitutes the observable clock, not TPU microcode execution.
		if (m_peripheral[offset] & 0x3000)
			m_clock_timer->adjust(attotime::from_hz(8192), 0, attotime::from_hz(8192));
		else
		{
			m_clock_timer->adjust(attotime::never);
			m_cpu->set_input_line(6, CLEAR_LINE);
		}
	}
}

TIMER_CALLBACK_MEMBER(ds90tl_state::clock_tick)
{
	if (++m_clock_ticks <= 3)
		std::fprintf(stderr, "DS90 CLOCK tick=%u pc=%08x sr=%04x vector=%08x\n", m_clock_ticks,
			u32(m_cpu->pc()), u16(m_cpu->state_int(M68K_SR)),
			m_cpu->space(AS_PROGRAM).read_dword(m_cpu->state_int(M68K_VBR) + 0x78));
	m_cpu->set_input_line(6, ASSERT_LINE);
}

// Host terminal byte transport: deliberately bypasses serial framing/modem pins.
ds90tl_state::~ds90tl_state()
{
	for (unsigned port = 0; port < 8; ++port)
	{
		if (m_pty[port] >= 0) ::close(m_pty[port]);
		if (m_pty_slave[port] >= 0) ::close(m_pty_slave[port]);
		m_pty[port] = m_pty_slave[port] = -1;
	}
}

TIMER_CALLBACK_MEMBER(ds90tl_state::serial_poll)
{
	if (serial_stop_requested) { machine().schedule_exit(); return; }
	for (unsigned port = 0; port < 8; ++port)
	{
		if (m_pty[port] < 0) continue;
		auto &pending = m_serial_output[port];
		while (!pending.empty())
		{
			const u8 byte = pending.front();
			if (::write(m_pty[port], &byte, 1) != 1) break;
			pending.pop_front();
		}
		duart_channel &channel = port & 1 ? *m_uart[port / 2]->m_chanB : *m_uart[port / 2]->m_chanA;
		if (!(channel.read_chan_reg(1) & 1))
		{
			u8 byte;
			if (::read(m_pty[port], &byte, 1) == 1)
			{
				channel.rx_fifo_push(byte, 0);
				std::fprintf(stderr, "DS90 PTY-RX port=%u byte=%02x\n", port + 1, byte);
			}
		}
	}
}

TIMER_CALLBACK_MEMBER(ds90tl_state::uart_probe)
{
	if (!m_probe_port || m_probe_count >= m_probe_data.size()) return;
	const unsigned port = m_probe_port - 1;
	duart_channel &channel = port & 1 ? *m_uart[port / 2]->m_chanB : *m_uart[port / 2]->m_chanA;
	if (channel.read_chan_reg(1) & 1)
	{
		m_probe_timer->adjust(attotime::from_seconds(1)); // diagnostic backpressure
		return;
	}
	const u8 data = m_probe_data[m_probe_count];
	std::fprintf(stderr, "DS90 FIFO-INJECT port=%u byte=%02x csr=%02x mr1=%02x mr2=%02x sr=%02x tx_rate=%d\n",
		m_probe_port, data, channel.get_chan_CSR(), channel.read_MR1(), channel.read_MR2(),
		channel.read_chan_reg(1), channel.get_tx_rate());
	// Diagnostic FIFO injection only: bypasses receiver enable, framing,
	// baud clocks and modem pins. Wait for an empty FIFO before the next byte.
	channel.rx_fifo_push(data, 0);
	if (++m_probe_count < m_probe_data.size()) m_probe_timer->adjust(attotime::from_seconds(1));
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
	if ((offset == 3 || offset == 11) && !machine().side_effects_disabled())
		std::fprintf(stderr, "DS90 UART-RX port=%u byte=%02x pc=%08x\n",
			Block * 2 + (offset == 11) + 1, value, u32(m_cpu->pc()));
	record("READ-UART", 0x400000 + Block * 0x20 + offset * 2, value, mask);
	return u16(value) << 8; // guest uses byte registers at even addresses
}

template<unsigned Block> void ds90tl_state::uart_w(offs_t offset, u16 data, u16 mask)
{
	record("WRITE-UART", 0x400000 + Block * 0x20 + offset * 2, data, mask);
	if (mask & 0xff00)
	{
		const u8 value = data >> 8;
		const unsigned port = Block * 2 + (offset >= 8);
		duart_channel &channel = offset >= 8 ? *m_uart[Block]->m_chanB : *m_uart[Block]->m_chanA;
		const u8 before = channel.read_chan_reg(1);
		if (offset == 3 || offset == 11)
			std::fprintf(stderr, "DS90 UART-TX port=%u byte=%02x char=%c sr_before=%02x\n",
				Block * 2 + (offset == 11) + 1, value, value >= 32 && value < 127 ? value : '.', before);
		if ((offset == 3 || offset == 11) && m_pty[port] >= 0)
		{
			if (m_serial_output[port].size() >= 65536)
				fatalerror("Serial output queue full on port %u; attach a terminal\n", port + 1);
			m_serial_output[port].push_back(value);
		}
		m_uart[Block]->write(offset, value);
		if ((offset == 2 || offset == 10) && m_uart_commands[port]++ < 32)
			std::fprintf(stderr, "DS90 UART-CMD port=%u byte=%02x sr_before=%02x sr_after=%02x pc=%08x\n",
				port + 1, value, before, channel.read_chan_reg(1), u32(m_cpu->pc()));
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
	// Provisional erased configuration-store window. Firmware checksum and
	// readback routines address bytes relative to 0x100c00; size unconfirmed.
	map(0x100000, 0x10ffff).ram().share("configram");
	map(0x200000, 0x200005).r(FUNC(ds90tl_state::identity_r));
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
	m_serial_timer = timer_alloc(FUNC(ds90tl_state::serial_poll), this);
	const char *serial = std::getenv("DS90_SERIAL_PTY");
	if (serial && std::string_view(serial) == "1")
	{
		serial_stop_requested = 0;
		std::signal(SIGINT, serial_stop);
		std::signal(SIGTERM, serial_stop);
		for (unsigned port = 0; port < 8; ++port)
		{
			m_pty[port] = ::posix_openpt(O_RDWR | O_NOCTTY | O_NONBLOCK);
			if (m_pty[port] < 0 || ::grantpt(m_pty[port]) || ::unlockpt(m_pty[port]))
				fatalerror("Cannot allocate serial PTY: %s\n", std::strerror(errno));
			const char *path = ::ptsname(m_pty[port]);
			if (!path) fatalerror("Cannot resolve serial PTY\n");
			// Keep the slave open across terminal disconnects and disable echo.
			m_pty_slave[port] = ::open(path, O_RDWR | O_NOCTTY | O_NONBLOCK);
			termios settings{};
			if (m_pty_slave[port] < 0 || ::tcgetattr(m_pty_slave[port], &settings))
				fatalerror("Cannot configure serial PTY\n");
			::cfmakeraw(&settings);
			if (::tcsetattr(m_pty_slave[port], TCSANOW, &settings)) fatalerror("Cannot set raw serial PTY\n");
			std::fprintf(stderr, "DS90 SERIAL port=%u path=%s\n", port + 1, path);
		}
		m_serial_timer->adjust(attotime::from_msec(1), 0, attotime::from_msec(1));
	}
	m_observer = timer_alloc(FUNC(ds90tl_state::observe), this);
	m_tpu_timer = timer_alloc(FUNC(ds90tl_state::tpu_complete), this);
	m_clock_timer = timer_alloc(FUNC(ds90tl_state::clock_tick), this);
	m_probe_timer = timer_alloc(FUNC(ds90tl_state::uart_probe), this);
}

void ds90tl_state::machine_reset()
{
	auto &space = m_cpu->space(AS_PROGRAM);
	m_clock_timer->adjust(attotime::never);
	m_cpu->set_input_line(6, CLEAR_LINE);
	m_probe_timer->adjust(attotime::never);
	const char *probe = std::getenv("DS90_UART_PROBE_PORT");
	m_probe_port = probe ? std::clamp(std::atoi(probe), 0, 8) : 0;
	m_probe_count = m_serial_events = 0;
	m_probe_data.clear();
	const char *probe_hex = std::getenv("DS90_UART_PROBE_HEX");
	const std::string hex = probe_hex ? probe_hex : "0d0d0d";
	if (hex.size() > 256 || (hex.size() & 1)) fatalerror("Invalid diagnostic UART input length\n");
	for (unsigned i = 0; i < hex.size(); i += 2)
	{
		const std::string byte = hex.substr(i, 2);
		char *end = nullptr;
		const unsigned long value = std::strtoul(byte.c_str(), &end, 16);
		if (end != byte.c_str() + 2) fatalerror("Invalid diagnostic UART hex input\n");
		m_probe_data.push_back(u8(value));
	}
	std::fill(std::begin(m_uart_commands), std::end(m_uart_commands), 0);
	if (m_probe_port)
	{
		const char *when = std::getenv("DS90_UART_PROBE_AT");
		m_probe_timer->adjust(attotime::from_seconds(when ? std::clamp(std::atoi(when), 1, 55) : 20));
	}
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
	// ROM port-diagnostic state, not a presence mask: startup ORs the
	// transient word into both halves of the persistent status longword.
	// Report healthy ports. 0x00ff incorrectly marks every port unavailable.
	space.write_dword(0x80500e, 0);
	space.write_word(0x80501e, 0);
	// Boot ROM normally validates board-configuration records. With no ROM
	// implementation, request firmware defaults for the three metadata groups
	// tested at 0x07940696..0x079406da (bits 19, 20, 21).
	space.write_dword(0x805016, space.read_dword(0x805016) | 0x00380000);
	// Firmware fatal-report callback normally belongs to the inherited ROM.
	// Preserve its report fields and stop, rather than jumping through zero.
	m_boot[0x1400 / 2] = 0x60fe;
	space.write_dword(0x8051a2, 0x1400);
	m_events = m_ticks = m_clock_ticks = 0;
	std::fprintf(stderr, "DS90 BOOT image=MNENG3 ram=4194304 entry=078713f8 sp=07bff000 vbr=0\n"
		"DS90 EXPERIMENTAL handoff: synthetic vectors/RAM-size; TPU completion substitution; no network backend\n");
	m_observer->adjust(attotime::from_msec(1), 0, attotime::from_msec(1));
}

TIMER_CALLBACK_MEMBER(ds90tl_state::observe)
{
	const u32 pc = m_cpu->pc();
	const u32 sp = m_cpu->state_int(M68K_SP);
	if (pc == 0x1400)
	{
		auto &space = m_cpu->space(AS_PROGRAM);
		dump_state();
		for (unsigned i = 0; i < 64; ++i)
			std::fprintf(stderr, "DS90 REPORT-STACK address=%08x data=%08x\n", sp + i * 4,
				space.read_dword(sp + i * 4));
		for (unsigned reg : { M68K_A4, M68K_A5 })
		{
			const u32 base = m_cpu->state_int(reg);
			if ((base & 0xffffff) < 0x800000 || (base & 0xffffff) > 0xbfffc0) continue;
			for (unsigned i = 0; i < 16; ++i)
				std::fprintf(stderr, "DS90 OBJECT address=%08x data=%08x\n", base + i * 4,
					space.read_dword(base + i * 4));
		}
		fatalerror("DS90 firmware fatal code=%04x caller=%08x parameter=%08x report_sp=%08x\n",
			space.read_word(0x805036), space.read_dword(0x805028),
			space.read_dword(0x805032), space.read_dword(0x80502c));
	}
	if (pc >= 0x1000 && pc < 0x1400)
	{
		dump_state();
		for (unsigned i = 0; i < 32; ++i)
			std::fprintf(stderr, "DS90 STACK address=%08x data=%08x\n", sp + i * 4,
				m_cpu->space(AS_PROGRAM).read_dword(sp + i * 4));
		fatalerror("DS90 inherited exception vector=%u pc=%08x sp=%08x saved_pc=%08x\n",
			(pc - 0x1000) / 4, pc, sp, m_cpu->space(AS_PROGRAM).read_dword(sp + 2));
	}
	if (++m_ticks <= 10 || m_ticks % 100 == 0)
		std::fprintf(stderr, "DS90 PROGRESS ms=%u pc=%08x sp=%08x sr=%04x clock_ticks=%u guest_us=%08x\n",
			m_ticks, pc, sp, u16(m_cpu->state_int(M68K_SR)), m_clock_ticks,
			m_cpu->space(AS_PROGRAM).read_dword(0xfff024));
}

void ds90tl_state::ds90tl(machine_config &config)
{
	// SYNCR=0x9b00 selects W=1, X=0, Y=27. With a provisional
	// 32768 Hz reference: 32768 * 4 * (27+1) * 2^(2*1+0).
	DS90_CPU(config, m_cpu, 14'680'064); // reference crystal not measured
	m_cpu->set_addrmap(AS_PROGRAM, &ds90tl_state::memory_map);
	AM7990(config, m_lance, 20'000'000);
	// File-backed approximation only; physical storage and write protocol
	// are not yet identified. Preserve bytes across resets and invocations.
	NVRAM(config, "configram", nvram_device::DEFAULT_ALL_1);
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
	ROM_LOAD("mneng3.sys", 0, 0x18b600, CRC(5275e52d) SHA1(df36a007dd3da3b6dbacf96318787e5e07d7f378))
ROM_END

} // anonymous namespace

COMP(1992, ds90tl, 0, 0, ds90tl, ds90tl, ds90tl_state, empty_init,
	"Digital Equipment Corporation", "DECserver 90TL (MNENG3 bring-up)", MACHINE_NOT_WORKING | MACHINE_NO_SOUND_HW)
