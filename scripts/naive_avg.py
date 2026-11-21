#!/usr/bin/env python3
"""Naive-Avg baseline.

Naive-Avg predicts the next trials-to-discovery (TTD) as the running mean
of every TTD observed so far:

    naive[r] = mean(TTD[0 .. r-1])

It needs no model and no fuzzer instrumentation, so it is derived here
from the TrialsToDisc column of the per-benchmark CSVs rather than being
emitted by the patched fuzzer. It is scored exactly like every other
estimator: converted to time units by dividing by Rate, with row 0 and
Rate=0 rows dropped, under the same W-SMAPE / UE / OE definitions used in
CELL-11 of main_analysis.ipynb.

Writes data/csv/naive_avg.csv and prints the Table VII row.

Usage:  python3 scripts/naive_avg.py        (run from the repo root)
"""
import csv
import math
import os
import sys

import numpy as np

FILES = ['freetype2.1', 'json.1', 'libpcap.1', 'libpng.1',
         'libxml.1', 'zlib.1', 're2-2014-12-09', 'libjpeg.1']


def naive_avg(ttd):
    """Running mean of all previously observed TTD. Index 0 has no history."""
    return [float(round(sum(ttd[:i]) / i)) for i in range(1, len(ttd))]


def table2_metrics(y_true, y_pred, rate):
    """Same definitions as calculate_table2_metrics in CELL-11."""
    y_true = np.asarray(y_true, float)
    y_pred = np.asarray(y_pred, float)
    rate = np.asarray(rate, float)
    mask = np.isfinite(y_true) & np.isfinite(y_pred) & (y_true > 0) & (y_pred > 0)
    y_true, y_pred, r = y_true[mask], y_pred[mask], rate[mask]
    if len(y_true) == 0:
        return dict(UE_Cnt=0, UE_Pct=0.0, OE_Max=0.0, OE_Avg=0.0, SMAPE=0.0)
    valid = r != 0
    y_true = y_true[valid] / r[valid]
    y_pred = y_pred[valid] / r[valid]

    errors = y_pred - y_true
    under = errors < 0
    ue_cnt = int(np.sum(under))
    ue_pct = round(ue_cnt / len(errors) * 100, 2)

    over = errors > 0
    if np.any(over):
        v = errors[over]
        oe_max = round(math.log10(v.max()), 2) if v.max() > 0 else 0.0
        oe_avg = round(math.log10(v.mean()), 2) if v.mean() > 0 else 0.0
    else:
        oe_max = oe_avg = 0.0

    denom = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    denom = np.where(denom == 0, 1e-9, denom)
    weights = np.where(y_pred < y_true, 2.0, 1.0)
    smape = round(float(np.mean(weights * np.abs(y_pred - y_true) / denom) * 100), 2)

    return dict(UE_Cnt=ue_cnt, UE_Pct=ue_pct,
                OE_Max=oe_max, OE_Avg=oe_avg, SMAPE=smape)


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rows = []
    for name in FILES:
        path = os.path.join(root, 'data', 'csv', name + '.csv')
        if not os.path.exists(path):
            sys.exit('missing %s -- run the notebook first' % path)
        with open(path) as fh:
            recs = list(csv.DictReader(fh))
        ttd_all = [float(r['TrialsToDisc']) for r in recs]
        pred = naive_avg(ttd_all)
        scored = recs[1:]                      # CELL-11 drops row 0
        gt = [float(r['TrialsToDisc']) for r in scored]
        rate = [float(r['Rate']) if r['Rate'] not in ('', 'nan') else 1.0
                for r in scored]
        m = table2_metrics(gt, pred, rate)
        m['Benchmark'] = name
        rows.append(m)

    out = os.path.join(root, 'data', 'csv', 'naive_avg.csv')
    cols = ['Benchmark', 'UE_Cnt', 'UE_Pct', 'OE_Max', 'OE_Avg', 'SMAPE']
    with open(out, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r[c] for c in cols})

    print('Naive-Avg per benchmark')
    print('-' * 62)
    print(f"{'Benchmark':<18}{'W-SMAPE':>10}{'UE-Pct':>10}{'OE-Max':>10}{'OE-Avg':>10}")
    for r in rows:
        print(f"{r['Benchmark']:<18}{r['SMAPE']:>10.2f}{r['UE_Pct']:>10.2f}"
              f"{r['OE_Max']:>10.2f}{r['OE_Avg']:>10.2f}")

    def ms(key):
        v = [r[key] for r in rows]
        return np.mean(v), np.std(v, ddof=1)

    print('-' * 62)
    print('Table VII row (mean +- sample std across the eight benchmarks):')
    for label, key in [('W-SMAPE', 'SMAPE'), ('UE-Rate', 'UE_Pct'),
                       ('OE-Max', 'OE_Max'), ('OE-Avg', 'OE_Avg')]:
        mu, sd = ms(key)
        print(f'  {label:<9} {mu:8.2f} +- {sd:5.2f}')
    print('\nSaved: data/csv/naive_avg.csv')


if __name__ == '__main__':
    main()
