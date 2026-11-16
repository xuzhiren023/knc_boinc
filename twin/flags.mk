# Compile only gravity differently; reuse every other baseline card object.
include Makefile
VARIANT ?= V0
FLAGS_V0 := -O2
FLAGS_V1 := -O3
FLAGS_V2 := -mphinix -ffp-contract=off
FLAGS_V3 := -O2 -funroll-loops
FLAG_OUT := ../build/flags/$(VARIANT)
FLAG_OBJECT := $(FLAG_OUT)/nbody_grav.o
.PHONY: flag-variant
flag-variant: $(FLAG_OUT)/milkyway_nbody.mic
$(FLAG_OBJECT): $(UPSTREAM)/nbody/src/nbody_grav.c ../twin/flags.mk
	@$(TOOLCHAIN)/mkdir -p $(FLAG_OUT) ../build/tmp
	$(CC) $(CPPFLAGS) $(filter-out -O2,$(CFLAGS)) $(FLAGS_$(VARIANT)) -c $< -o $@
$(FLAG_OUT)/milkyway_nbody.mic: $(FLAG_OBJECT) $(OBJECTS)
	$(CXX) $(COMMON_LDFLAGS) $(filter-out $(OUT)/nbody/src/nbody_grav.c.o,$(OBJECTS)) $(FLAG_OBJECT) $(COMMON_LDLIBS) -o $@
