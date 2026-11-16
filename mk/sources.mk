# Standalone source manifest; paths relative to the pinned upstream root.
# Derived from upstream nbody/, milkyway/, lua/, popt/, dSFMT/CMakeLists.txt.
NBODY_SOURCES := \
 nbody/src/main.c \
 nbody/src/nbody_chisq.c nbody/src/nbody_grav.c nbody/src/nbody_io.c \
 nbody/src/nbody_curses.c nbody/src/nbody_types.c nbody/src/nbody_tree.c \
 nbody/src/nbody_orbit_integrator.c nbody/src/nbody_potential.c \
 nbody/src/nbody_bessel.c nbody/src/nbody_virial.c nbody/src/nbody_density.c \
 nbody/src/nbody_friction.c nbody/src/nbody.c nbody/src/nbody_plain.c \
 nbody/src/nbody_check_params.c nbody/src/nbody_isotropic.c \
 nbody/src/nbody_mixeddwarf.c nbody/src/nbody_manual_bodies.c \
 nbody/src/nbody_dwarf_potential.c nbody/src/nbody_plummer.c \
 nbody/src/nbody_nfw.c nbody/src/nbody_hernq.c nbody/src/nbody_show.c \
 nbody/src/nbody_checkpoint.c nbody/src/nbody_defaults.c \
 nbody/src/nbody_coordinates.c nbody/src/nbody_util.c nbody/src/nbody_emd.c \
 nbody/src/nbody_mass.c nbody/src/nbody_devoptions.c \
 nbody/src/nbody_likelihood.c nbody/src/nbody_histogram.c \
 nbody/src/nbody_caustic.c nbody/src/nbody_particle_data.c \
 nbody/src/nbody_king_model.c nbody/src/nbody_math_funcs.c \
 nbody/src/nbody_lua.c nbody/src/nbody_lua_models.c \
 nbody/src/nbody_lua_util.c nbody/src/nbody_lua_misc.c \
 nbody/src/nbody_lua_types/nbody_lua_types.c \
 nbody/src/nbody_lua_types/nbody_lua_type_marshal.c \
 nbody/src/nbody_lua_types/nbody_lua_nbodystate.c \
 nbody/src/nbody_lua_types/nbody_lua_nbodyctx.c \
 nbody/src/nbody_lua_types/nbody_lua_body.c \
 nbody/src/nbody_lua_types/nbody_lua_halo.c \
 nbody/src/nbody_lua_types/nbody_lua_disk.c \
 nbody/src/nbody_lua_types/nbody_lua_spherical.c \
 nbody/src/nbody_lua_types/nbody_lua_dwarf.c \
 nbody/src/nbody_lua_types/nbody_lua_potential.c \
 nbody/src/nbody_lua_types/nbody_lua_histogram_params.c
MW_SOURCES := \
 milkyway/src/milkyway_util.c milkyway/src/milkyway_alloc.c \
 milkyway/src/milkyway_rename.c milkyway/src/milkyway_boinc_util.cc \
 milkyway/src/milkyway_show.c milkyway/src/milkyway_cpuid.c \
 milkyway/src/milkyway_timing.c milkyway/src/milkyway_math_funcs.c \
 milkyway/src/milkyway_lua_marshal.c milkyway/src/milkyway_lua_util.c \
 milkyway/src/milkyway_lua_math.c milkyway/src/milkyway_lua_vector.c \
 milkyway/src/milkyway_lua_dsfmt.c milkyway/src/milkyway_lua_types.c
LUA_SOURCES := \
 lua/src/lapi.c lua/src/lcode.c lua/src/ldebug.c lua/src/ldo.c \
 lua/src/ldump.c lua/src/lfunc.c lua/src/lgc.c lua/src/llex.c \
 lua/src/lmem.c lua/src/lobject.c lua/src/lopcodes.c lua/src/lparser.c \
 lua/src/lstate.c lua/src/lstring.c lua/src/ltable.c lua/src/ltm.c \
 lua/src/lundump.c lua/src/lvm.c lua/src/lzio.c lua/src/lauxlib.c \
 lua/src/lbaselib.c lua/src/ldblib.c lua/src/liolib.c lua/src/lmathlib.c \
 lua/src/loslib.c lua/src/ltablib.c lua/src/lstrlib.c lua/src/linit.c \
 lua/src/loadlib.c
BUNDLED_SOURCES := $(LUA_SOURCES) dSFMT/dSFMT.c \
 popt/src/popt.c popt/src/poptparse.c popt/src/poptconfig.c \
 popt/src/popthelp.c popt/src/poptint.c
SOURCES := $(NBODY_SOURCES) $(MW_SOURCES) $(BUNDLED_SOURCES)
# IEEE math, no host-specific ISA flags; scalar dSFMT also builds on KNC.
COMMON_CFLAGS := -O2 -g -fopenmp -fno-strict-aliasing -ffp-contract=off -fno-math-errno
COMMON_CPPFLAGS := -D_GNU_SOURCE -DDOUBLEPREC=1 -DDSFMT_MEXP=19937 -DHAVE_CONFIG_H
INCLUDE_DIRS := milkyway/include nbody/include lua/include lua/src popt/include dSFMT
C_LANGUAGE_FLAGS := -std=gnu99
CXX_LANGUAGE_FLAGS := -std=gnu++11
COMMON_LDFLAGS := -fopenmp
COMMON_LDLIBS := -lm
NBODY_LUA_CPPFLAGS := -DNBODY_LUA_TYPES_COMPILATION
MW_LUA_CPPFLAGS := -DMILKYWAY_LUA_COMPILATION
MW_MATH_CPPFLAGS := -DMILKYWAY_MATH_COMPILATION

# Exact bundled crlibm source list from crlibm/CMakeLists.txt.
CRLIBM_SOURCES := $(addprefix crlibm/,crlibm_private.c triple-double.c \
 exp-td.c exp-td-standalone.c expm1-standalone.c expm1.c log.c log1p.c \
 rem_pio2_accurate.c trigo_fast.c trigo_accurate.c trigpi.c asincos.c pow.c \
 atan_fast.c atan_accurate.c csh_fast.c scs_lib/scs_private.c \
 scs_lib/addition_scs.c scs_lib/division_scs.c scs_lib/print_scs.c \
 scs_lib/double2scs.c scs_lib/zero_scs.c scs_lib/multiplication_scs.c scs_lib/scs2double.c)
SOURCES += $(CRLIBM_SOURCES)
INCLUDE_DIRS += crlibm
COMMON_CPPFLAGS += -DSCS_NB_WORDS=8 -DSCS_NB_BITS=30
