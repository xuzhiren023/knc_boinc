# Shared non-generator objects have identical release options in all variants.
include Makefile
ifneq ($(strip $(DFS_FLAGS)),)
CFLAGS += $(DFS_FLAGS)
endif
ifneq ($(strip $(DFS_LIBS)),)
COMMON_LDLIBS := $(DFS_LIBS) $(COMMON_LDLIBS)
endif
DFS_COMMON := $(filter-out $(COMMON_OUT)/nbody/src/nbody_mixeddwarf.c.o,$(addprefix $(COMMON_OUT)/,$(addsuffix .o,$(SOURCES))))
DFS_PROGRAM := $(if $(filter card,$(TARGET)),milkyway_nbody.mic,milkyway_nbody.exe)
DFS_INCLUDES := -I$(DFS_TREE)/nbody/include
$(OUT)/generator.o: $(DFS_TREE)/nbody/src/nbody_mixeddwarf.c $(DFS_TREE)/nbody/include/nbody_df_special.h ../src/nbody_df_vector8.h $(OUT)/.build-options
	$(CC) $(DFS_INCLUDES) $(CPPFLAGS) $(CFLAGS) -fopt-info-vec-missed=$(abspath $(OUT))/vec-missed.txt -MMD -MP -c $< -o $@
$(OUT)/dfs-program: $(DFS_COMMON) $(OUT)/generator.o
	$(CXX) $(COMMON_LDFLAGS) $^ $(COMMON_LDLIBS) -o $@
$(OUT)/capture.o: $(DFS_CAPTURE) ../tests/s10_df_capture.h ../tests/quad_capture.h $(DFS_TREE)/nbody/include/nbody_df_special.h ../src/nbody_df_vector8.h $(OUT)/.build-options
	$(CC) $(DFS_INCLUDES) $(CPPFLAGS) $(CFLAGS) -I../tests -c $< -o $@
$(OUT)/capture.exe: $(DFS_COMMON) $(OUT)/capture.o
	$(CXX) $(COMMON_LDFLAGS) $^ $(COMMON_LDLIBS) -o $@
$(OUT)/kernel.o: ../tests/s10_df_vector8_kernel.c $(DFS_TREE)/nbody/include/nbody_df_special.h ../src/nbody_df_vector8.h $(OUT)/.build-options
	$(CC) $(DFS_INCLUDES) $(CPPFLAGS) $(CFLAGS) -I$(DFS_TREE)/nbody/src -c $< -o $@
$(OUT)/kernel.exe: $(filter-out $(COMMON_OUT)/nbody/src/main.c.o,$(DFS_COMMON)) $(OUT)/kernel.o
	$(CXX) $(COMMON_LDFLAGS) $^ $(COMMON_LDLIBS) -o $@
.PHONY: dfs-app dfs-capture dfs-kernel
dfs-app: $(OUT)/dfs-program
	$(TOOLCHAIN)/cp $< $(OUT)/$(DFS_PROGRAM)
dfs-capture: $(OUT)/capture.exe
dfs-kernel: $(OUT)/kernel.exe
$(OUT)/twin-kernel.o: ../probes/s10_df_vector8_twin.c ../src/nbody_df_vector8.h $(OUT)/.build-options
	$(CC) $(DFS_INCLUDES) $(CPPFLAGS) $(CFLAGS) -I$(DFS_TREE)/nbody/src -c $< -o $@
$(OUT)/twin-kernel.mic: $(filter-out $(COMMON_OUT)/nbody/src/main.c.o,$(DFS_COMMON)) $(OUT)/twin-kernel.o
	$(CXX) $(COMMON_LDFLAGS) $^ $(COMMON_LDLIBS) -o $@
.PHONY: dfs-twin
dfs-twin: $(OUT)/twin-kernel.mic
-include $(OUT)/generator.d
