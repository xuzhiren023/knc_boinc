include Makefile
.PHONY: df-capture
$(OUT)/df-capture.o: $(DF_CAPTURE_SOURCE) ../tests/quad_capture.h $(OUT)/.build-options
	$(CC) $(CPPFLAGS) $(CFLAGS) -I../tests $(if $(DF_SOURCE),-I$(dir $(DF_SOURCE))../include) -c $< -o $@
$(OUT)/capture.exe: $(filter-out $(OUT)/nbody/src/nbody_mixeddwarf.c.o,$(OBJECTS)) $(OUT)/df-capture.o
	$(CXX) $(COMMON_LDFLAGS) $^ $(COMMON_LDLIBS) -o $@
df-capture: $(OUT)/capture.exe
.PHONY: df-kernel
$(OUT)/df-kernel.o: ../tests/s9_df_kernel.c $(UPSTREAM)/nbody/src/nbody_mixeddwarf.c $(dir $(DF_SOURCE))../include/nbody_df_vector.h $(OUT)/.build-options
	$(CC) $(CPPFLAGS) $(CFLAGS) -I$(dir $(DF_SOURCE)) -I$(dir $(DF_SOURCE))../include -c $< -o $@
$(OUT)/kernel.exe: $(filter-out $(OUT)/nbody/src/main.c.o $(OUT)/nbody/src/nbody_mixeddwarf.c.o,$(OBJECTS)) $(OUT)/df-kernel.o
	$(CXX) $(COMMON_LDFLAGS) $^ $(COMMON_LDLIBS) -o $@
df-kernel: $(OUT)/kernel.exe
