.DEFAULT_GOAL := x86
ROOT := ..
UPSTREAM := $(ROOT)/third_party/milkywayathome_client
TOOLCHAIN ?= /cygdrive/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin
SHELL := $(TOOLCHAIN)/bash.exe
# Use Cygwin make and tools, not MinGW/MSVC. Override TOOLCHAIN for another installation.
CC := $(TOOLCHAIN)/gcc
CXX := $(TOOLCHAIN)/g++
export PATH := $(TOOLCHAIN):$(PATH)
include sources.mk
OUT := $(ROOT)/build/x86
OBJECTS := $(addprefix $(OUT)/,$(addsuffix .o,$(SOURCES)))
CPPFLAGS := $(COMMON_CPPFLAGS) -I$(ROOT)/config $(addprefix -I$(UPSTREAM)/,$(INCLUDE_DIRS))
CFLAGS := $(COMMON_CFLAGS) $(C_LANGUAGE_FLAGS)
CXXFLAGS := $(COMMON_CFLAGS) $(CXX_LANGUAGE_FLAGS)
# Always local scratch, even when invoked directly from a fresh checkout.
export TMPDIR := $(shell $(TOOLCHAIN)/cygpath -am $(ROOT)/build/tmp)
export TMP := $(TMPDIR)
export TEMP := $(TMPDIR)
.PHONY: x86
x86: $(OUT)/milkyway_nbody.exe
$(OUT)/milkyway_nbody.exe: $(OBJECTS)
	$(CXX) $(COMMON_LDFLAGS) $^ $(COMMON_LDLIBS) -o $@
$(OUT)/%.c.o: $(UPSTREAM)/%.c sources.mk $(wildcard $(ROOT)/config/*.h)
	@$(TOOLCHAIN)/mkdir -p $(dir $@) ../build/tmp
	$(CC) $(CPPFLAGS) $(CFLAGS) -MMD -MP -c $< -o $@
$(OUT)/%.cc.o: $(UPSTREAM)/%.cc sources.mk $(wildcard $(ROOT)/config/*.h)
	@$(TOOLCHAIN)/mkdir -p $(dir $@) ../build/tmp
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -MMD -MP -c $< -o $@
$(filter $(OUT)/nbody/src/nbody_lua%,$(OBJECTS)): CPPFLAGS += $(NBODY_LUA_CPPFLAGS)
$(filter $(OUT)/milkyway/src/milkyway_lua%,$(OBJECTS)): CPPFLAGS += $(MW_LUA_CPPFLAGS)
$(OUT)/milkyway/src/milkyway_math_funcs.c.o: CPPFLAGS += $(MW_MATH_CPPFLAGS)
-include $(OBJECTS:.o=.d)

include boinc.mk
