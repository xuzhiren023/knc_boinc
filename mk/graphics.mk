GRAPHICS_OUT := $(ROOT)/build/graphics
.PHONY: graphics graphics-test
graphics: $(GRAPHICS_OUT)/knc_nbody_graphics.exe
graphics-test: $(GRAPHICS_OUT)/format.exe $(GRAPHICS_OUT)/format-card.o $(GRAPHICS_OUT)/graphics_test.exe
$(GRAPHICS_OUT)/knc_nbody_graphics.exe: $(ROOT)/src/knc_nbody_graphics.cpp $(ROOT)/src/knc_graphics_format.h $(BOINC_OUT)/libboinc_api.a
	@$(TOOLCHAIN)/mkdir -p $(dir $@) ../build/tmp
	$(CXX) $(BOINC_CPPFLAGS) $(BOINC_CXXFLAGS) $< -Wl,--gc-sections $(BOINC_OUT)/libboinc_api.a $(BOINC_LDLIBS) -lopengl32 -lgdi32 -o $@
$(GRAPHICS_OUT)/format.exe: $(ROOT)/tests/graphics_format.c $(ROOT)/src/knc_graphics_format.h
	@$(TOOLCHAIN)/mkdir -p $(dir $@) ../build/tmp
	$(TOOLCHAIN)/gcc -std=c11 -I$(ROOT)/src $< -o $@
$(GRAPHICS_OUT)/format-card.o: $(ROOT)/tests/graphics_format.c $(ROOT)/src/knc_graphics_format.h
	@$(TOOLCHAIN)/mkdir -p $(dir $@) ../build/tmp
	$(KNC_ROOT)/bin/k1om-mpss-linux-gcc -march=knc -std=c11 -I$(ROOT)/src -c $< -o $@
$(GRAPHICS_OUT)/graphics_test.exe: $(ROOT)/tests/graphics_test.cpp $(ROOT)/src/knc_graphics_format.h $(BOINC_OUT)/libboinc_api.a
	@$(TOOLCHAIN)/mkdir -p $(dir $@) ../build/tmp
	$(CXX) $(BOINC_CPPFLAGS) $(BOINC_CXXFLAGS) -I$(ROOT)/src $< -Wl,--gc-sections $(BOINC_OUT)/libboinc_api.a $(BOINC_LDLIBS) -lgdi32 -o $@
