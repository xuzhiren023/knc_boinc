# Full workunit 117676 generation proof

`params.lua` is the unchanged full 110,000-body Lua retained by S7-02 in
`runs/real/x86-12/nbody_parameters.lua`. The integration proof copies it after
checking S8-05's checkpoint-reference provenance. It uses the original fourteen
arguments and seed 65477096, with the core-small OCS histogram (identical input
data). Unlike core-small, body counts and evolution time are not reduced.

`bash scripts/s8-09.sh proof` builds an observation-only generator executable,
dumps seven binary64 fields per body after center-of-mass corrections, and exits
after full generation. It compares all 6,160,000 bytes with initial body rows
recovered from the two independent S7-02 step-one checkpoints. Their retained
initial best-likelihood body tables are identical. Provenance, input hash and
raw rows are under `runs/s8-09/final/`. This is generation proof; it does not run
the full 1,568-step evolution or establish a full-task card speed.
