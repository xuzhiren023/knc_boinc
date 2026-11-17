# Rejected S9-05 vector experiment

`performance.patch`: **Performance**, `NBODY_DF_VECTOR=0`, requires reuse.
`instrumentation.patch`: **Instrumentation**, `NBODY_DF_STATS=0`, counters only.
These are deliberately outside `scripts/fetch.sh`'s ordinary patch sequence.

Apply after ordinary patches only to the isolated tree:

```bash
source scripts/s9-df-common.sh
python scripts/s9-df.py experiment
bash scripts/build-s9-df.sh x86-dfvector x86 1 1
```

The evidence driver and `scripts/test-s9-df.sh` reproduce the kernel and body
proofs. See `docs/research/s9-df-bound.md` for the error argument. Core-small:
3,245/4,000 exact body replays (81.125%); generation 41.9036431 s versus
18.2441604 s for exact reuse, at 12 threads. Bodies and likelihood bits match.
The ticket's stop rule rejects the vector path; the card/full run select reuse.
No vector card run or full vector generation is staged or claimed.
