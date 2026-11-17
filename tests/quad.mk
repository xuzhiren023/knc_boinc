# Compile an instrumented generator; all other objects use the real app build.
include Makefile
$(OUT)/nbody/src/nbody_mixeddwarf.c.o: $(CAPTURE_SOURCE) ../tests/quad_capture.h
	@$(TOOLCHAIN)/mkdir -p $(dir $@) ../build/tmp
	$(CC) $(CPPFLAGS) $(CFLAGS) -I../tests -MMD -MP -c $(CAPTURE_SOURCE) -o $@
