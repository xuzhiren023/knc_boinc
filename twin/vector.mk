# Capture replay links the same gravity object as the corresponding app.
include Makefile
VROOT := ../build/vector/$(TARGET)-$(if $(filter 1,$(VECTOR_GRAVITY)),on,off)
VOBJ := $(VROOT)/replay.o
VGRAV := $(VROOT)/exposed-grav.o
VOBJCOPY := $(if $(filter card,$(TARGET)),$(KNC_ROOT)/../toolchain/cross/bin/k1om-mpss-linux-objcopy,$(TOOLCHAIN)/objcopy)
$(VGRAV): $(OUT)/nbody/src/nbody_grav.c.o
	$(VOBJCOPY) --globalize-symbol=nbGravity $< $@
$(VOBJ): ../twin/vector/replay.c ../twin/vector/replay_blocks.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -I../twin/vector -c $< -o $@
.PHONY: vector-replay
vector-replay: $(OBJECTS) $(VGRAV) $(VOBJ)
	$(CXX) $(COMMON_LDFLAGS) $(filter-out $(OUT)/nbody/src/main.c.o $(OUT)/nbody/src/nbody_grav.c.o,$(OBJECTS)) $(VGRAV) $(VOBJ) $(COMMON_LDLIBS) -o $(VROOT)/replay.exe
