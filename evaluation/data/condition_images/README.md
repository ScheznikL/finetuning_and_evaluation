# condition_images/

Empty in the repository. Put the 100 condition images here (`<uuid>.png`, RGBA after background removal).

The INIT/CKPT8000 runs all reuse the images of `batch_generation_results`
(`100_test_images/<uuid>.png`), so one set of 100 images covers every cell of the 2x2 analyses.
ControlNet runs write their own images to `<run>/100_test_images/`.
