# Reuse identical non-generator objects from the baseline target. GEN_* macros
# occur only in the generator TU; all release flags match the baseline.
include Makefile
GEN_COMMON_OBJECTS := $(filter-out $(COMMON_OUT)/nbody/src/nbody_mixeddwarf.c.o,$(addprefix $(COMMON_OUT)/,$(addsuffix .o,$(SOURCES))))
GEN_EXE := $(if $(filter card,$(TARGET)),milkyway_nbody.mic,milkyway_nbody.exe)
$(OUT)/gen.o: $(UPSTREAM)/nbody/src/nbody_mixeddwarf.c $(UPSTREAM)/nbody/include/nbody_gen_profile.h $(OUT)/.build-options
	$(CC) $(CPPFLAGS) $(CFLAGS) -MMD -MP -c $< -o $@
$(OUT)/gen-program: $(GEN_COMMON_OBJECTS) $(OUT)/gen.o
	$(CXX) $(COMMON_LDFLAGS) $^ $(COMMON_LDLIBS) -o $@
.PHONY: gen-app gen-capture
gen-app: $(OUT)/gen-program
	$(TOOLCHAIN)/cp $< $(OUT)/$(GEN_EXE)
$(OUT)/capture.o: ../build/s10/gen/mixeddwarf-capture.c ../tests/quad_capture.h ../build/s10/gen/nbody_gen_profile.h $(OUT)/.build-options
	$(CC) $(CPPFLAGS) $(CFLAGS) -I../tests -c $< -o $@
$(OUT)/capture.exe: $(GEN_COMMON_OBJECTS) $(OUT)/capture.o
	$(CXX) $(COMMON_LDFLAGS) $^ $(COMMON_LDLIBS) -o $@
gen-capture: $(OUT)/capture.exe
-include $(OUT)/gen.d
