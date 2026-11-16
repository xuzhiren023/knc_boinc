.DEFAULT_GOAL := x86
ROOT := ..
UPSTREAM := $(ROOT)/third_party/milkywayathome_client
TOOLCHAIN ?= /cygdrive/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin
SHELL := $(TOOLCHAIN)/bash.exe
# Use Cygwin make and tools, not MinGW/MSVC. Override TOOLCHAIN for another installation.
TARGET ?= x86
KNC_ROOT ?= /cygdrive/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/gcc-knc-16.2.0
ifeq ($(TARGET),card)
CC := $(KNC_ROOT)/bin/k1om-mpss-linux-gcc
CXX := $(KNC_ROOT)/bin/k1om-mpss-linux-g++
TARGET_FLAGS := -march=knc
# 256 chunks at 1,024 bodies; 5,000 at 20,000 bodies. See S5-02.
FORCE_CHUNK ?= 4
PROGRAM := milkyway_nbody.mic
else
CC := $(TOOLCHAIN)/gcc
CXX := $(TOOLCHAIN)/g++
PROGRAM := milkyway_nbody.exe
endif
export PATH := $(TOOLCHAIN):$(PATH)
include sources.mk
OUT := $(ROOT)/build/$(TARGET)
OBJECTS := $(addprefix $(OUT)/,$(addsuffix .o,$(SOURCES)))
CPPFLAGS := $(COMMON_CPPFLAGS) -I$(ROOT)/config -I$(ROOT)/src $(addprefix -I$(UPSTREAM)/,$(INCLUDE_DIRS))
ifneq ($(strip $(FORCE_CHUNK)),)
CPPFLAGS += -DNBODY_FORCE_CHUNK=$(FORCE_CHUNK)
endif
CFLAGS := $(COMMON_CFLAGS) $(TARGET_FLAGS) $(C_LANGUAGE_FLAGS)
CXXFLAGS := $(COMMON_CFLAGS) $(TARGET_FLAGS) $(CXX_LANGUAGE_FLAGS)
# Always local scratch, even when invoked directly from a fresh checkout.
export TMPDIR := $(shell $(TOOLCHAIN)/cygpath -am $(ROOT)/build/tmp)
export TMP := $(TMPDIR)
export TEMP := $(TMPDIR)
ifeq ($(TARGET),card)
# DT_RPATH, not RUNPATH: dependencies of bundled runtimes must find peers too.
COMMON_LDFLAGS += -Wl,--disable-new-dtags,-rpath,'$$ORIGIN:$$ORIGIN/../lib'
endif
.PHONY: x86 card program
x86:
	$(MAKE) TARGET=x86 program
card:
	$(MAKE) TARGET=card program
	$(SHELL) ../scripts/package_card.sh
program: $(OUT)/$(PROGRAM)
$(OUT)/$(PROGRAM): $(OBJECTS) Makefile
	$(CXX) $(COMMON_LDFLAGS) $(OBJECTS) $(COMMON_LDLIBS) -o $@
$(OUT)/%.c.o: $(UPSTREAM)/%.c sources.mk Makefile $(wildcard $(ROOT)/config/*.h) $(ROOT)/src/knc_graphics_format.h
	@$(TOOLCHAIN)/mkdir -p $(dir $@) ../build/tmp
	$(CC) $(CPPFLAGS) $(CFLAGS) -MMD -MP -c $< -o $@
$(OUT)/%.cc.o: $(UPSTREAM)/%.cc sources.mk Makefile $(wildcard $(ROOT)/config/*.h) $(ROOT)/src/knc_graphics_format.h
	@$(TOOLCHAIN)/mkdir -p $(dir $@) ../build/tmp
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -MMD -MP -c $< -o $@
$(filter $(OUT)/nbody/src/nbody_lua%,$(OBJECTS)): CPPFLAGS += $(NBODY_LUA_CPPFLAGS)
$(filter $(OUT)/milkyway/src/milkyway_lua%,$(OBJECTS)): CPPFLAGS += $(MW_LUA_CPPFLAGS)
$(OUT)/milkyway/src/milkyway_math_funcs.c.o: CPPFLAGS += $(MW_MATH_CPPFLAGS)
-include $(OBJECTS:.o=.d)

include boinc.mk

include graphics.mk
