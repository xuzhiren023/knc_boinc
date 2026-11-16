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
