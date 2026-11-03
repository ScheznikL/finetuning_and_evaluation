# meshes/

Empty in the repository. Put generated meshes here to re-run the measurements.

Layout per run (same as the generation scripts write it):

```
<run>/100_test_models/<uuid>.glb
<run>/100_test_models/<uuid>_meta.json   # or <uuid>.json: uuid, seed, prompt, metrics{time_t2i, time_shape}
```

`<run>` is a run name from `evaluation/seeds/seeds_by_run.csv`, e.g. `batch_INIT_mm_detailed_100_res`.
