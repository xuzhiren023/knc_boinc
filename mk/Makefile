.DEFAULT_GOAL := x86
ROOT := ..
UPSTREAM := $(ROOT)/third_party/milkywayathome_client_196
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
# S6-01 is opt-in; enabling the card default remains the lead's call.
VECTOR_GRAVITY ?= 0
CPPFLAGS += -DNBODY_VECTOR_GRAVITY=$(VECTOR_GRAVITY)
PHASE_TIMERS ?= 0
STATIC_INTEGRATE ?= 0
CPPFLAGS += -DNBODY_PHASE_TIMERS=$(PHASE_TIMERS) -DNBODY_STATIC_INTEGRATE=$(STATIC_INTEGRATE)
# Independent mixed-dwarf quadrature nodes; explicitly enabled for S8 card.
PARALLEL_QUAD ?= 0
CPPFLAGS += -DNBODY_PARALLEL_QUAD=$(PARALLEL_QUAD)
GEN_PIPELINE ?= 0
CPPFLAGS += -DNBODY_GEN_PIPELINE=$(GEN_PIPELINE)
GEN_PROFILE ?= 0
CPPFLAGS += -DNBODY_GEN_PROFILE=$(GEN_PROFILE)
DF_REUSE ?= 0
DF_VECTOR ?= 0
DF_STATS ?= 0
DF_SOURCE ?=
ifeq ($(DF_VECTOR),1)
ifeq ($(strip $(DF_SOURCE)),)
$(error DF_VECTOR is a rejected experiment: use scripts/build-s9-df.sh with vector=1)
endif
endif
CPPFLAGS += -DNBODY_DF_REUSE=$(DF_REUSE) -DNBODY_DF_VECTOR=$(DF_VECTOR) -DNBODY_DF_STATS=$(DF_STATS)
TREE_VARIANT ?= 0
TREE_IDENTITY ?= 0
WALK_LAYOUT ?= 0
WALK_COUNTERS ?= 0
WALK_PROFILE ?= 0
WALK_PROOF ?= 0
WALK_PREFETCH ?= 0
WALK_HOT ?= 0
WALK_SCHEDULE ?= 0
CPPFLAGS += -DNBODY_WALK_PROFILE=$(WALK_PROFILE) -DNBODY_WALK_PROOF=$(WALK_PROOF)
CPPFLAGS += -DNBODY_WALK_PREFETCH=$(WALK_PREFETCH) -DNBODY_WALK_HOT=$(WALK_HOT) -DNBODY_WALK_SCHEDULE=$(WALK_SCHEDULE)
CPPFLAGS += -DNBODY_TREE_VARIANT=$(TREE_VARIANT) -DNBODY_TREE_IDENTITY=$(TREE_IDENTITY)
CPPFLAGS += -DNBODY_WALK_LAYOUT=$(WALK_LAYOUT) -DNBODY_WALK_COUNTERS=$(WALK_COUNTERS)
# PGO is opt-in; both compilation and linking need its runtime flags.
PGOFLAGS ?=
CFLAGS := $(PGOFLAGS) $(COMMON_CFLAGS) $(TARGET_FLAGS) $(C_LANGUAGE_FLAGS)
CXXFLAGS := $(PGOFLAGS) $(COMMON_CFLAGS) $(TARGET_FLAGS) $(CXX_LANGUAGE_FLAGS)
# Always local scratch, even when invoked directly from a fresh checkout.
export TMPDIR := $(shell $(TOOLCHAIN)/cygpath -am $(ROOT)/build/tmp)
export TMP := $(TMPDIR)
export TEMP := $(TMPDIR)
ifeq ($(TARGET),card)
# DT_RPATH, not RUNPATH: dependencies of bundled runtimes must find peers too.
COMMON_LDFLAGS += -Wl,--disable-new-dtags,-rpath,'$$ORIGIN:$$ORIGIN/../lib'
endif
ifeq ($(TARGET),card)
ifeq ($(DF_VECTOR),1)
CFLAGS += -mveclibabi=knc
endif
endif
COMMON_LDFLAGS += $(PGOFLAGS)
.PHONY: x86 card program
# Track the complete compile/link configuration, including command-line flags.
# Integration experiments must not silently reuse objects from another variant.
.PHONY: build-config-check
build-config-check:
$(OUT)/.build-options: build-config-check
	@$(TOOLCHAIN)/mkdir -p $(OUT)
	@printf '%s\n' '$(CPPFLAGS)' '$(CFLAGS)' '$(CXXFLAGS)' '$(COMMON_LDFLAGS)' '$(COMMON_LDLIBS)' > $@.tmp
	@$(TOOLCHAIN)/cmp -s $@.tmp $@ || $(TOOLCHAIN)/cp $@.tmp $@
	@$(TOOLCHAIN)/rm -f $@.tmp
$(OBJECTS): $(OUT)/.build-options
# Reusing an OUT directory must not silently keep the other macro setting.
.PHONY: phase-config-check
phase-config-check:
$(OUT)/.phase-options: phase-config-check
	@$(TOOLCHAIN)/mkdir -p $(OUT)
	@printf '%s\n' '$(PHASE_TIMERS) $(STATIC_INTEGRATE)' > $@.tmp
	@$(TOOLCHAIN)/cmp -s $@.tmp $@ || $(TOOLCHAIN)/cp $@.tmp $@
	@$(TOOLCHAIN)/rm -f $@.tmp
$(addprefix $(OUT)/nbody/src/,$(addsuffix .c.o,main nbody nbody_plain nbody_grav)): $(OUT)/.phase-options
.PHONY: vector-config-check
vector-config-check:
$(OUT)/.vector-gravity: vector-config-check
	@$(TOOLCHAIN)/mkdir -p $(OUT)
	@printf '%s\n' '$(VECTOR_GRAVITY)' > $@.tmp
	@$(TOOLCHAIN)/cmp -s $@.tmp $@ || $(TOOLCHAIN)/cp $@.tmp $@
	@$(TOOLCHAIN)/rm -f $@.tmp
$(OUT)/nbody/src/nbody_grav.c.o: $(OUT)/.vector-gravity
.PHONY: quad-config-check
quad-config-check:
$(OUT)/.parallel-quad: quad-config-check
	@$(TOOLCHAIN)/mkdir -p $(OUT)
	@echo '$(PARALLEL_QUAD)' > $@.tmp
	@$(TOOLCHAIN)/cmp -s $@.tmp $@ || $(TOOLCHAIN)/cp $@.tmp $@
	@$(TOOLCHAIN)/rm -f $@.tmp
$(OUT)/nbody/src/nbody_mixeddwarf.c.o: $(OUT)/.parallel-quad
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
ifneq ($(strip $(DF_SOURCE)),)
$(OUT)/nbody/src/nbody_mixeddwarf.c.o: $(DF_SOURCE) $(dir $(DF_SOURCE))../include/nbody_df_vector.h
	@$(TOOLCHAIN)/mkdir -p $(dir $@) ../build/tmp
	$(CC) $(CPPFLAGS) $(CFLAGS) -I$(dir $(DF_SOURCE))../include -MMD -MP -c $(DF_SOURCE) -o $@
endif
$(filter $(OUT)/nbody/src/nbody_lua%,$(OBJECTS)): CPPFLAGS += $(NBODY_LUA_CPPFLAGS)
$(filter $(OUT)/milkyway/src/milkyway_lua%,$(OBJECTS)): CPPFLAGS += $(MW_LUA_CPPFLAGS)
-include $(OBJECTS:.o=.d)

include boinc.mk

include graphics.mk
