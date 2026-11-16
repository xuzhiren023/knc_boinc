# App-side subset only; no BOINC client/server/manager or graphics renderer.
BOINC := $(ROOT)/third_party/boinc
BOINC_OUT := $(ROOT)/build/boinc
BOINC_SOURCES := api/boinc_api.cpp api/graphics2_util.cpp lib/app_ipc.cpp \
 lib/filesys.cpp lib/parse.cpp lib/util.cpp lib/shmem.cpp lib/miofile.cpp \
 lib/coproc.cpp lib/wslinfo.cpp lib/opencl_boinc.cpp lib/procinfo.cpp lib/procinfo_win.cpp lib/mfile.cpp \
 lib/str_util.cpp lib/diagnostics.cpp lib/diagnostics_win.cpp lib/proc_control.cpp lib/mem_usage.cpp \
 lib/hostinfo.cpp lib/prefs.cpp lib/proxy_info.cpp lib/url.cpp lib/win_util.cpp
BOINC_OBJECTS := $(addprefix $(BOINC_OUT)/,$(BOINC_SOURCES:.cpp=.o))
BOINC_CPPFLAGS := -D_WIN32 -D_WIN64 -DWIN32 -D__CYGWIN32__ -DHAVE_CONFIG_H -include config.h \
 -I$(ROOT)/config/boinc -I$(BOINC) -I$(BOINC)/lib -I$(BOINC)/api
BOINC_CXXFLAGS := -O2 -std=gnu++17 -ffunction-sections -fdata-sections
BOINC_LDLIBS := -ladvapi32 -lpsapi -luser32 -lshell32 -lole32 -lws2_32
.PHONY: boinc-api boinc-api-test
boinc-api: $(BOINC_OUT)/libboinc_api.a
$(BOINC_OUT)/libboinc_api.a: $(BOINC_OBJECTS)
	$(TOOLCHAIN)/ar rcs $@ $^
$(BOINC_OUT)/%.o: $(BOINC)/%.cpp boinc.mk $(wildcard $(ROOT)/config/boinc/*.h)
	@$(TOOLCHAIN)/mkdir -p $(dir $@) ../build/tmp
	$(CXX) $(BOINC_CPPFLAGS) $(BOINC_CXXFLAGS) -MMD -MP -c $< -o $@
boinc-api-test: $(BOINC_OUT)/boinc_app.exe $(BOINC_OUT)/boinc_fake_client.exe
$(BOINC_OUT)/%.exe: $(ROOT)/tests/%.cpp $(BOINC_OUT)/libboinc_api.a
	$(CXX) $(BOINC_CPPFLAGS) $(BOINC_CXXFLAGS) $< -Wl,--gc-sections $(BOINC_OUT)/libboinc_api.a $(BOINC_LDLIBS) -o $@
-include $(BOINC_OBJECTS:.o=.d)
