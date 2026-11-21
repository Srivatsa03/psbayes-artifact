# Instrumented libFuzzer and campaign launch

The campaigns in `data/raw/` were produced by a patched libFuzzer running
under FuzzBench. This directory holds everything needed to rebuild it.

## Pins

| Component | Pin |
|---|---|
| FuzzBench (upstream base) | `2a2ca6a` — "Fix CI (#2072)" on `google/fuzzbench` |
| FuzzBench (fork actually run) | `afc0fed` on https://github.com/Srivatsa03/fuzzbench |
| LLVM / compiler-rt | `d8981ce5b9f8caa567613b2bf5aa3095e0156130` |

The fork differs from upstream only by the local benchmark setup; the
estimator instrumentation lives entirely in the patch below.

## Files

| File | What it is |
|---|---|
| `libfuzzer-psbayes.patch` | The libFuzzer patch. Adds per-seed IDs, per-seed trial accounting, and the `__SUCCS__` / `__FAILS__` / `__FEATS__` / `__LLAPL__` / `__LGDTU__` / `__MXFRK__` / `__AVFRK__` / `__RATES__` trace lines that `data/raw/*.txt` is made of. |
| `builder.Dockerfile` | Clones LLVM at the pin above and applies the patch. |
| `runner.Dockerfile` | Runtime image. |
| `fuzzer.py` | FuzzBench fuzzer driver. |

`LLaplace` and `LGT` are computed *inside* the patched fuzzer, in
`CalcEst()`. They are read out of the trace, not recomputed by the
notebook. Each aggregates a per-seed discovery rate over the corpus using
libFuzzer's entropic scheduling density and scales it by the number of
mutations executed so far. Neither takes a confidence level.

## Rebuilding and launching

```bash
git clone https://github.com/Srivatsa03/fuzzbench && cd fuzzbench
git checkout afc0fed
cp /path/to/this/dir/libfuzzer-psbayes.patch fuzzers/libfuzzer/patch1.diff
cp /path/to/this/dir/builder.Dockerfile      fuzzers/libfuzzer/
cp /path/to/this/dir/runner.Dockerfile       fuzzers/libfuzzer/
cp /path/to/this/dir/fuzzer.py               fuzzers/libfuzzer/

# one benchmark, 24h, as used for the paper
PYTHONPATH=. python3 experiment/run_experiment.py \
  --experiment-name psbayes-json \
  --fuzzers libfuzzer \
  --benchmarks json \
  --experiment-config experiment-config.yaml
```

Benchmarks run for the paper: `freetype2`, `json`, `libjpeg`, `libpcap`,
`libpng`, `libxml2`, `re2-2014-12-09`, `zlib`. Each produced one trace,
shipped as `data/raw/<benchmark>_run2.txt`.

## Trace format

Eight lines per discovery round. See section 6 of the top-level README.
