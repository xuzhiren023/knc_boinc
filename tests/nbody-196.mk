# S7-01 first-force capture, linked with the same objects as each real app.
include Makefile
.PHONY: capture
capture: $(OUT)/capture.exe
$(OUT)/s7-capture.c.o: ../build/s7-capture.c Makefile sources.mk
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
$(OUT)/capture.exe: $(filter-out $(OUT)/nbody/src/nbody_grav.c.o,$(OBJECTS)) $(OUT)/s7-capture.c.o
	$(CXX) $(COMMON_LDFLAGS) $^ $(COMMON_LDLIBS) -o $@
