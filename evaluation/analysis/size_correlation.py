"""
Check whether generated model size depends on the size requested in the prompt.

measure_batch.py reports mesh extents * 1000 as "mm", so dividing by 1000
recovers the raw model units (Hunyuan3D normalises output to roughly [-1, 1]).

Usage:
    python size_correlation.py path/to/detailed_results.json [more.json ...]
"""
import sys
import json
import numpy as np

try:
    from scipy import stats
except ImportError:
    stats = None


def get_model_dims(entry):
    # Newer runs use 'model_dimensions_original', older ones 'model_dimensions'
    return entry.get('model_dimensions_original') or entry['model_dimensions']


def analyse(json_path):
    with open(json_path) as f:
        data = json.load(f)

    requested_mm = []
    longest_units = []
    length_units = []
    for entry in data:
        dims = get_model_dims(entry)
        requested_mm.append(entry['prompt_dimensions']['total_length'])
        # Raw model units = reported "mm" / 1000
        longest_units.append(max(dims['total_length'], dims['width_x'], dims['depth_z']) / 1000)
        length_units.append(dims['total_length'] / 1000)

    requested_mm = np.array(requested_mm)
    longest_units = np.array(longest_units)
    length_units = np.array(length_units)

    print(f"\n{json_path}")
    print(f"  Objects: {len(data)}")
    print(f"  Longest side (model units): min={longest_units.min():.3f}  "
          f"median={np.median(longest_units):.3f}  max={longest_units.max():.3f}")
    print(f"  Requested total length (mm): min={requested_mm.min():.0f}  max={requested_mm.max():.0f}")

    for name, generated in [('longest side', longest_units), ('total_length axis', length_units)]:
        # Pearson r and least-squares slope (model units per requested mm)
        r = np.corrcoef(requested_mm, generated)[0, 1]
        slope, intercept = np.polyfit(requested_mm, generated, 1)
        line = f"  Requested vs generated {name}: r = {r:.3f}, slope = {slope:.2e} units/mm"
        if stats is not None:
            line += f", p = {stats.pearsonr(requested_mm, generated)[1]:.3f}"
        print(line)


if __name__ == '__main__':
    for path in sys.argv[1:]:
        analyse(path)
