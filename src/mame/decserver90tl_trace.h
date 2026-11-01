// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <cstdio>
#include <cstdlib>
#include <cstring>

inline bool ds90_trace_enabled()
{
	static const bool enabled = [] {
		const char *value = std::getenv("DS90_TRACE");
		return value && !std::strcmp(value, "1");
	}();
	return enabled;
}

// Gate arguments as well as formatting and writes in the hot diagnostic paths.
#define DS90_TRACE(...) do { if (ds90_trace_enabled()) std::fprintf(stderr, __VA_ARGS__); } while (false)
