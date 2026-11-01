// SPDX-License-Identifier: BSD-3-Clause
// DECserver-only application layer using the unmodified MAME core/SDL OSD.
#include "emu.h"
#include "drivenum.h"
#include "emuopts.h"
#include "main.h"
#include "ui/uimain.h"
#include "modules/lib/osdobj_common.h"

#include <algorithm>
#include <cstdio>
#include <memory>
#include <sstream>
#include <string_view>

GAME_EXTERN(ds90tl);

// Standalone targets supply their own driver registry and version hooks.
const game_driver *const driver_list::s_drivers_sorted[] = {
	&GAME_NAME(___empty),
	&GAME_NAME(ds90tl),
};
std::size_t const driver_list::s_driver_count = 2;

namespace {

class ds90_machine_manager final : public machine_manager
{
public:
	ds90_machine_manager(emu_options &options, osd_interface &osd)
		: machine_manager(options, osd) { }

	ui_manager *create_ui(running_machine &machine) override
	{
		// Core services expect a UI object. The base class is deliberately
		// inert and does not link any src/frontend/mame UI implementation.
		m_ui = std::make_unique<ui_manager>(machine);
		return m_ui.get();
	}

	int execute()
	{
		bool reset;
		int result;
		do
		{
			{
				machine_config config(GAME_NAME(ds90tl), m_options);
				running_machine machine(config, *this);
				set_machine(&machine);
				result = machine.run(false);
				reset = machine.hard_reset_pending() && !machine.exit_pending();
				set_machine(nullptr);
			}
			m_ui.reset();
		}
		while (!result && reset);
		return result;
	}

private:
	std::unique_ptr<ui_manager> m_ui;
};

bool has_argument(const std::vector<std::string> &args, std::string_view wanted)
{
	return std::find(args.begin(), args.end(), wanted) != args.end();
}

} // anonymous namespace

int emulator_info::start_frontend(emu_options &options, osd_interface &osd, std::vector<std::string> &args)
{
	if (has_argument(args, "-help") || has_argument(args, "--help") || has_argument(args, "-h"))
	{
		std::puts("DECserver 90TL standalone headless runtime\n"
			"Use run.sh or tools/run_mneng3.py for firmware, PTY, TAP and serialsim setup.\n"
			"Core/OSD runtime options are accepted; video and sound are forced to none.\n"
			"Lua, plugins, menus, debug UI, HTTP serving and INI loading are unavailable.\n"
			"Build with --full-frontend for Lua diagnostics. -showconfig lists options.");
		return EMU_ERR_NONE;
	}
	if (has_argument(args, "-version") || has_argument(args, "--version"))
	{
		std::printf("DECserver 90TL standalone / MAME %s\n", get_build_version());
		return EMU_ERR_NONE;
	}
	try
	{
		options.set_default_value(OPTION_PLUGINS, "0");
		options.set_default_value(OPTION_READCONFIG, "0");
		options.set_system_name("ds90tl");
		// These options belong to the application layer, not emu_options.
		auto parsed = args;
		const bool show_config = has_argument(parsed, "-showconfig");
		parsed.erase(std::remove(parsed.begin(), parsed.end(), "-showconfig"), parsed.end());
		options.parse_command_line(parsed, OPTION_PRIORITY_CMDLINE);
		if (std::string_view(options.system_name()) != "ds90tl")
			throw options_error_exception("Only the ds90tl system is supported");
		if (options.console() || options.autoboot_script()[0] || options.autoboot_command()[0]
			|| options.plugins() || options.debug() || options.http() || options.read_config())
			throw options_error_exception("Lua/plugins/debug UI/HTTP/INI loading require --full-frontend");
		options.set_value(OSDOPTION_VIDEO, "none", OPTION_PRIORITY_MAXIMUM);
		options.set_value(OSDOPTION_SOUND, "none", OPTION_PRIORITY_MAXIMUM);
		options.set_value(OPTION_SKIP_GAMEINFO, 1, OPTION_PRIORITY_MAXIMUM);
		osd.set_verbose(options.verbose());
		if (show_config)
		{
			std::ostringstream output;
			options.output_ini(output);
			std::fputs(output.str().c_str(), stdout);
			return EMU_ERR_NONE;
		}
		std::fprintf(stderr, "DS90 FRONTEND standalone (no Lua or menu frontend)\n");
		ds90_machine_manager manager(options, osd);
		// running_machine requires the HTTP manager object even when disabled.
		// OPTION_HTTP was rejected above, so this does not open a listener.
		manager.start_http_server();
		return manager.execute();
	}
	catch (options_exception const &error)
	{
		std::fprintf(stderr, "DECserver options: %s\n", error.what());
		return EMU_ERR_INVALID_CONFIG;
	}
	catch (emu_fatalerror const &error)
	{
		std::fprintf(stderr, "DECserver startup: %s\n", error.what());
		return error.exitcode();
	}
	catch (std::exception const &error)
	{
		std::fprintf(stderr, "DECserver startup: %s\n", error.what());
		return EMU_ERR_FATALERROR;
	}
}

int emulator_info::start_frontend(emu_options &options, osd_interface &osd, int argc, char *argv[])
{
	std::vector<std::string> args(argv, argv + argc);
	return start_frontend(options, osd, args);
}

const char *emulator_info::get_appname() { return "DECserver 90TL"; }
const char *emulator_info::get_appname_lower() { return "decserver90tl"; }
const char *emulator_info::get_configname() { return "decserver90tl"; }
const char *emulator_info::get_copyright() { return "DECserver 90TL standalone runtime; MAME core contributors"; }
const char *emulator_info::get_copyright_info() { return get_copyright(); }
const char *emulator_info::get_bare_build_version() { return "0.289"; }
const char *emulator_info::get_build_version() { return "0.289 (pinned 2692d09218b6, DECserver standalone)"; }
void emulator_info::display_ui_chooser(running_machine &) { }
bool emulator_info::draw_user_interface(running_machine &) { return false; }
void emulator_info::periodic_check() { }
bool emulator_info::frame_hook() { return false; }
void emulator_info::sound_hook(const std::map<std::string, std::vector<std::pair<const float *, int>>> &) { }
void emulator_info::layout_script_cb(layout_file &, const char *) { }
bool emulator_info::standalone() { return true; }
