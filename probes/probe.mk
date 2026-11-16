include Makefile
PROBE := $(ROOT)/build/$(TARGET)/libm_probe$(if $(filter card,$(TARGET)),.mic,.exe)
.PHONY: libm-probe
libm-probe: $(PROBE)
$(OUT)/libm_probe.o: $(ROOT)/probes/libm_probe.c sources.mk $(ROOT)/probes/probe.mk
	@$(TOOLCHAIN)/mkdir -p $(OUT) ../build/tmp
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
$(PROBE): $(OUT)/libm_probe.o $(filter $(OUT)/crlibm/%,$(OBJECTS))
	$(CXX) $(COMMON_LDFLAGS) $^ $(COMMON_LDLIBS) -o $@
.PHONY: fildl-host
fildl-host:
	$(CC) $(CPPFLAGS) $(CFLAGS) $(ROOT)/probes/fildl_host.c -o $(OUT)/fildl_host.exe
