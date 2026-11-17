include ../tests/s10-df-vector8.mk
$(OUT)/generator.o $(OUT)/capture.o $(OUT)/batch-kernel.o: ../src/nbody_df_batch.h
$(OUT)/capture.o: ../tests/s10_df_batch_capture.h $(dir $(DFS_CAPTURE))s10_df_batch_instrumented.h
$(OUT)/twin-kernel.o: ../src/nbody_df_batch.h $(DFS_TREE)/nbody/src/nbody_mixeddwarf.c
$(OUT)/batch-kernel.o: ../tests/s10_df_batch_kernel.c ../src/nbody_df_vector8.h $(DFS_TREE)/nbody/src/nbody_mixeddwarf.c $(OUT)/.build-options
	$(CC) $(DFS_INCLUDES) $(CPPFLAGS) $(CFLAGS) -I../tests -I$(DFS_TREE)/nbody/src -c $< -o $@
$(OUT)/batch-kernel.exe: $(filter-out $(COMMON_OUT)/nbody/src/main.c.o,$(DFS_COMMON)) $(OUT)/batch-kernel.o
	$(CXX) $(COMMON_LDFLAGS) $^ $(COMMON_LDLIBS) -o $@
.PHONY: dfb-kernel
dfb-kernel: $(OUT)/batch-kernel.exe
