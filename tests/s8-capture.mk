include Makefile
.PHONY: s8-capture
s8-capture: $(OUT)/capture.exe
$(OUT)/s8-capture.o: ../build/s8-09/mixeddwarf-capture.c ../tests/quad_capture.h $(OUT)/.build-options
	$(CC) $(CPPFLAGS) $(CFLAGS) -I../tests -c $< -o $@
$(OUT)/capture.exe: $(filter-out $(OUT)/nbody/src/nbody_mixeddwarf.c.o,$(OBJECTS)) $(OUT)/s8-capture.o
	$(CXX) $(COMMON_LDFLAGS) $^ $(COMMON_LDLIBS) -o $@
.PHONY: s8-tree-check
s8-tree-check: $(OUT)/tree-check.exe
$(OUT)/s8-tree-check.o: $(UPSTREAM)/nbody/src/nbody_tree.c $(OUT)/.build-options
	$(CC) $(CPPFLAGS) $(CFLAGS) -UNBODY_TREE_IDENTITY -DNBODY_TREE_IDENTITY=1 -c $< -o $@
$(OUT)/tree-check.exe: $(filter-out $(OUT)/nbody/src/nbody_tree.c.o,$(OBJECTS)) $(OUT)/s8-tree-check.o
	$(CXX) $(COMMON_LDFLAGS) $^ $(COMMON_LDLIBS) -o $@
.PHONY: s8-vector-bench
s8-vector-bench: $(OUT)/vector-bench.exe
$(OUT)/s8-vector-bench.o: $(UPSTREAM)/nbody/src/nbody_grav.c $(OUT)/.build-options ../src/nbody_walk_layout.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -UNBODY_VECTOR_GRAVITY -DNBODY_VECTOR_GRAVITY=1 -c $< -o $@
$(OUT)/vector-bench.exe: $(filter-out $(OUT)/nbody/src/nbody_grav.c.o,$(OBJECTS)) $(OUT)/s8-vector-bench.o
	$(CXX) $(COMMON_LDFLAGS) $^ $(COMMON_LDLIBS) -o $@
