// SPDX-License-Identifier: BSD-3-Clause
// Linux/POSIX persistence for the 90TL's memory-mapped configuration store.
// This device observes memory writes, never CLI commands. File bytes retain
// the previous generic MAME NVRAM format (native shared-memory representation).
#pragma once

#include "emuopts.h"

#include <cerrno>
#include <cstring>
#include <filesystem>
#include <fcntl.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <unistd.h>

class ds90_nvram_device;
DECLARE_DEVICE_TYPE(DS90_NVRAM, ds90_nvram_device)

class ds90_nvram_device : public device_t
{
public:
	ds90_nvram_device(const machine_config &config, const char *tag, device_t *owner, u32 clock)
		: device_t(config, DS90_NVRAM, tag, owner, clock), m_ready(*this, 0) { }
	~ds90_nvram_device() override { if (m_lock >= 0) ::close(m_lock); }
	auto ready_cb() { return m_ready.bind(); }

	void write(offs_t offset, u16 data, u16 mem_mask = ~0)
	{
		const u16 before = m_storage[offset];
		COMBINE_DATA(&m_storage[offset]);
		if (m_storage[offset] == before) return;
		m_dirty = true;
		m_last_write = machine().time();
		m_idle_since = attotime::never;
	}

protected:
	void device_start() override
	{
		auto *share = owner()->memshare(tag());
		if (!share) fatalerror("Missing configuration memory share\n");
		m_storage = static_cast<u16 *>(share->ptr());
		m_bytes = share->bytes();
		const std::filesystem::path directory(machine().options().nvram_directory());
		if (directory.string().find(';') != std::string::npos)
			fatalerror("90TL NVRAM requires one storage directory\n");
		// Preserve the existing single-device, no-BIOS 90TL filename.
		m_path = directory / machine().basename() / "configram";
		m_enabled = machine().options().nvram_save();
		if (m_enabled)
		{
			std::filesystem::create_directories(m_path.parent_path());
			const std::string lock_path = m_path.string() + ".lock";
			m_lock = ::open(lock_path.c_str(), O_RDWR | O_CREAT | O_CLOEXEC, 0600);
			if (m_lock < 0 || ::flock(m_lock, LOCK_EX | LOCK_NB))
				fatalerror("Cannot lock NVRAM %s: %s (another simulator may be using it)\n", m_path.string(), std::strerror(errno));
		}

		const int fd = ::open(m_path.c_str(), O_RDONLY | O_CLOEXEC);
		if (fd < 0)
		{
			if (errno != ENOENT) fatalerror("Cannot read NVRAM %s: %s\n", m_path.string(), std::strerror(errno));
			std::memset(m_storage, 0xff, m_bytes);
			m_dirty = true;
			std::fprintf(stderr, "DS90 STORAGE initialized erased store path=%s\n", m_path.c_str());
		}
		else
		{
			struct stat status{};
			bool valid = !::fstat(fd, &status) && S_ISREG(status.st_mode) && u64(status.st_size) == m_bytes;
			size_t done = 0;
			while (valid && done < m_bytes)
			{
				const ssize_t count = ::read(fd, reinterpret_cast<u8 *>(m_storage) + done, m_bytes - done);
				if (count < 0 && errno == EINTR) continue;
				if (count <= 0) { valid = false; break; }
				done += count;
			}
			::close(fd);
			if (!valid) fatalerror("NVRAM %s must be a readable %zu-byte regular file; left unchanged\n", m_path.string(), m_bytes);
			m_mode = status.st_mode & 0777;
			std::fprintf(stderr, "DS90 STORAGE loaded path=%s bytes=%zu\n", m_path.c_str(), m_bytes);
		}
		m_timer = timer_alloc(FUNC(ds90_nvram_device::poll), this);
		m_timer->adjust(attotime::from_msec(50), 0, attotime::from_msec(50));
	}

	void device_stop() override
	{
		// Never serialize a partial firmware transaction on shutdown or fatal
		// exit. Unlike generic NVRAM, no other writer truncates this file later.
		if (!m_enabled || !m_dirty || !machine().exit_pending()) return;
		if (m_ready()) checkpoint();
		else std::fprintf(stderr, "DS90 STORAGE pending firmware writes; retained last completed checkpoint\n");
	}

private:
	TIMER_CALLBACK_MEMBER(poll)
	{
		if (!m_enabled || !m_dirty) return;
		const auto now = machine().time();
		if (!m_ready()) { m_idle_since = attotime::never; return; }
		if (m_idle_since == attotime::never) m_idle_since = now;
		const auto settle = attotime::from_msec(250);
		if (now - m_last_write >= settle && now - m_idle_since >= settle) checkpoint();
	}

	void checkpoint()
	{
		std::string name = m_path.string() + ".tmp.XXXXXX";
		int fd = ::mkstemp(name.data());
		int error = fd < 0 ? errno : 0;
		if (!error && ::fchmod(fd, m_mode)) error = errno;
		size_t done = 0;
		while (!error && done < m_bytes)
		{
			const ssize_t count = ::write(fd, reinterpret_cast<u8 *>(m_storage) + done, m_bytes - done);
			if (count < 0 && errno == EINTR) continue;
			if (count <= 0) { error = count < 0 ? errno : EIO; break; }
			done += count;
		}
		if (!error && ::fsync(fd)) error = errno;
		if (fd >= 0 && ::close(fd) && !error) error = errno;
		if (!error && ::rename(name.c_str(), m_path.c_str())) error = errno;
		if (error)
		{
			::unlink(name.c_str());
			fatalerror("NVRAM checkpoint failed for %s: %s\n", m_path.string(), std::strerror(error));
		}
		const int directory = ::open(m_path.parent_path().c_str(), O_RDONLY | O_DIRECTORY | O_CLOEXEC);
		error = directory < 0 ? errno : 0;
		if (!error && ::fsync(directory)) error = errno;
		if (directory >= 0) ::close(directory);
		if (error) fatalerror("NVRAM directory sync failed for %s: %s\n", m_path.string(), std::strerror(error));
		m_dirty = false;
		std::fprintf(stderr, "DS90 STORAGE checkpoint saved path=%s bytes=%zu\n", m_path.c_str(), m_bytes);
	}

	devcb_read_line m_ready;
	u16 *m_storage = nullptr;
	size_t m_bytes = 0;
	std::filesystem::path m_path;
	int m_lock = -1;
	mode_t m_mode = 0600;
	bool m_enabled = true;
	bool m_dirty = false;
	attotime m_last_write = attotime::zero;
	attotime m_idle_since = attotime::never;
	emu_timer *m_timer = nullptr;
};
DEFINE_DEVICE_TYPE(DS90_NVRAM, ds90_nvram_device, "ds90nvram", "DECserver persistent configuration memory")
