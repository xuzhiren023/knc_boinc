# Invoked with Cygwin make -C mk -f ../twin/host.mk.
include Makefile
CAPTURE_OBJECT := ../build/capture_grav.o
$(CAPTURE_OBJECT): ../build/capture_grav.c ../twin/capture_helper.h ../twin/capture_multicore.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -I../twin -c $< -o $@
.PHONY: capture-host profile-host
capture-host: $(OBJECTS) $(CAPTURE_OBJECT) ../build/capture_log.o
	$(CXX) $(COMMON_LDFLAGS) $(filter-out $(OUT)/nbody/src/nbody_grav.c.o,$(OBJECTS)) $(CAPTURE_OBJECT) ../build/capture_log.o -Wl,--wrap=log_rn $(COMMON_LDLIBS) -o ../build/capture.exe
profile-host: $(OBJECTS)
	$(CXX) $(COMMON_LDFLAGS) $(OBJECTS) $(COMMON_LDLIBS) -o ../build/profile/milkyway_nbody.exe
.PHONY: capture-layout
capture-layout:
	$(CC) $(CPPFLAGS) $(CFLAGS) -c ../twin/layout.c -o ../build/layout-$(TARGET).o

../build/capture_log.o: ../twin/capture_log.c
	$(CC) $(CFLAGS) -c $< -o $@
# S1-07: same gravity source, host x87 precision-control replay.
.PHONY: x87-host
../build/x87_grav.o: ../build/x87_grav.c ../twin/x87_capture.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -mfpmath=387 -I../twin -c $< -o $@
x87-host: $(OBJECTS) ../build/x87_grav.o
	$(CXX) $(COMMON_LDFLAGS) $(filter-out $(OUT)/nbody/src/nbody_grav.c.o,$(OBJECTS)) ../build/x87_grav.o $(COMMON_LDLIBS) -o ../build/x87_gravity.exe
