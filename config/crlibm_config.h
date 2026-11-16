/* Hand-expanded crlibm config, little endian, portable double-double sources.
 * K1OM uses the x87 control-word path too; it has no SSE2. */
#ifndef _CRLIBM_CONFIG_H_
#define _CRLIBM_CONFIG_H_
#define HAVE_FENV_H 1
#define HAVE_FLOAT_H 1
#define HAVE_INTTYPES_H 1
#define CRLIBM_TYPECPU_AMD64 1
#define CRLIBM_HAS_FPU_CONTROL 1
#ifdef __CYGWIN__
/* Cygwin lacks fpu_control.h; crlibm_private.h supplies GETCW/SETCW asm. */
#define _FPU_DEFAULT 0x037f
#define _FPU_EXTENDED 0x0300
#define _FPU_DOUBLE 0x0200
#else
#define HAVE_FPU_CONTROL_H 1
#endif
#endif
