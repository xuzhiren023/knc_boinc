# Run with Cygwin make -C mk -f ../twin/chunk.mk TARGET=card chunk-driver.
include Makefile
CROSS_BIN := /cygdrive/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cross/bin
CHUNK_OBJ := ../build/gravity_chunk.o
EXPOSED_GRAV := ../build/chunk_nbody_grav.o
$(CHUNK_OBJ): ../twin/gravity_chunk.c
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
$(EXPOSED_GRAV): $(OUT)/nbody/src/nbody_grav.c.o
	$(CROSS_BIN)/k1om-mpss-linux-objcopy --globalize-symbol=nbGravity $< $@
.PHONY: chunk-driver
chunk-driver: $(OBJECTS) $(CHUNK_OBJ) $(EXPOSED_GRAV)
	$(CXX) $(COMMON_LDFLAGS) $(foreach obj,$(OBJECTS),$(if $(filter $(OUT)/nbody/src/nbody_grav.c.o,$(obj)),$(EXPOSED_GRAV),$(obj))) $(CHUNK_OBJ) $(COMMON_LDLIBS) -o ../build/gravity_chunk.mic
