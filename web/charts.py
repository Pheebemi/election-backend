"""Server-drawn SVG geometry for the live tallies (replaces the Recharts charts).

Each function returns plain numbers/strings for a template to place in an
<svg>; hover details come from data attributes read by static/web/js/portal.js.
"""
import json
import math


def nice_max(value):
    """A round axis maximum at or above ``value`` (e.g. 87_000 -> 100_000)."""
    if value <= 0:
        return 10
    exp = 10 ** math.floor(math.log10(value))
    for step in (1, 2, 2.5, 5, 10):
        if value <= step * exp:
            return int(step * exp)
    return int(10 * exp)


def short(n):
    if n >= 1_000_000:
        return f'{n / 1_000_000:g}M'
    if n >= 1000:
        return f'{n / 1000:g}k'
    return str(n)


def _ticks(top, count=4):
    return [round(top * i / count) for i in range(count + 1)]


def stacked_bars(lgas, parties, width=760, height=380):
    """Votes per LGA, one stacked bar per LGA in party order."""
    left, right, top_pad, bottom = 46, 8, 12, 78
    plot_w, plot_h = width - left - right, height - top_pad - bottom
    totals = [l['total'] for l in lgas]
    top = nice_max(max(totals, default=0))
    n = max(len(lgas), 1)
    slot = plot_w / n
    bar_w = slot * 0.62
    bars = []
    for i, lga in enumerate(lgas):
        x = left + i * slot + (slot - bar_w) / 2
        y = top_pad + plot_h
        segments = []
        by_abbr = {v['abbr']: v for v in lga['votes']}
        for p in parties:
            v = by_abbr.get(p['abbr'], {}).get('votes', 0)
            if not v:
                continue
            h = v / top * plot_h
            y -= h
            segments.append({'x': round(x, 1), 'y': round(y, 1), 'w': round(bar_w, 1), 'h': round(h, 1),
                             'color': p['color'], 'abbr': p['abbr']})
        bars.append({
            'segments': segments,
            'label_x': round(x + bar_w / 2, 1), 'label_y': top_pad + plot_h + 10, 'name': lga['name'],
            'hit_x': round(left + i * slot, 1), 'hit_w': round(slot, 1),
            'tooltip': json.dumps({'name': lga['name'], 'total': lga['total'],
                                   'rows': [{'abbr': v['abbr'], 'votes': v['votes'], 'pct': v['pct'],
                                             'color': v['color']} for v in lga['votes']]}),
        })
    grid = [{'y': round(top_pad + plot_h - t / top * plot_h, 1), 'label': short(t)} for t in _ticks(top)]
    return {'width': width, 'height': height, 'bars': bars, 'grid': grid,
            'left': left, 'right': width - right, 'plot_top': top_pad, 'plot_bottom': top_pad + plot_h}


def _arc(cx, cy, r, start_deg, end_deg):
    """SVG arc path, angles clockwise from 12 o'clock."""
    if end_deg - start_deg >= 359.999:
        end_deg = start_deg + 359.9
    a0, a1 = math.radians(start_deg - 90), math.radians(end_deg - 90)
    x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
    x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
    large = 1 if end_deg - start_deg > 180 else 0
    return f'M{x0:.3f} {y0:.3f} A{r:.3f} {r:.3f} 0 {large} 1 {x1:.3f} {y1:.3f}'


def radial(totals, size=320):
    """Concentric rings: each party's ring is as long as its share of the top party."""
    cx = cy = size / 2
    inner, outer = 40, size / 2 - 14
    n = max(len(totals), 1)
    band = (outer - inner) / n
    stroke = band * 0.72
    top = max((t['votes'] for t in totals), default=0)
    rings = []
    for i, t in enumerate(totals):
        r = outer - band * i - band / 2
        frac = t['votes'] / top if top else 0
        rings.append({
            'track': _arc(cx, cy, r, 0, 360),
            'arc': _arc(cx, cy, r, 0, 360 * frac) if frac > 0 else '',
            'stroke': round(stroke, 1), 'color': t['color'], 'abbr': t['abbr'],
            'label_x': round(cx + 6, 1), 'label_y': round(cy - r + 4, 1),
            'tooltip': json.dumps({'name': t['name'], 'total': t['votes'],
                                   'rows': [{'abbr': t['abbr'], 'votes': t['votes'], 'pct': t['pct'],
                                             'color': t['color']}]}),
        })
    return {'size': size, 'rings': rings}


def lines(lgas, parties, width=1100, height=320):
    """One line per party across the LGAs."""
    left, right, top_pad, bottom = 46, 16, 14, 64
    plot_w, plot_h = width - left - right, height - top_pad - bottom
    n = len(lgas)
    top = nice_max(max((v['votes'] for l in lgas for v in l['votes']), default=0))
    xs = [left + (plot_w * i / (n - 1) if n > 1 else plot_w / 2) for i in range(n)]
    series = []
    for p in parties:
        pts = []
        for i, lga in enumerate(lgas):
            v = next((x['votes'] for x in lga['votes'] if x['abbr'] == p['abbr']), 0)
            pts.append({'x': round(xs[i], 1), 'y': round(top_pad + plot_h - v / top * plot_h, 1), 'v': v})
        series.append({'abbr': p['abbr'], 'color': p['color'], 'points': pts,
                       'path': ' '.join(f"{'M' if j == 0 else 'L'}{pt['x']} {pt['y']}" for j, pt in enumerate(pts))})
    columns = [{
        'x': round(xs[i], 1), 'name': lga['name'],
        'hit_x': round(xs[i] - (plot_w / max(n - 1, 1)) / 2, 1), 'hit_w': round(plot_w / max(n - 1, 1), 1),
        'tooltip': json.dumps({'name': lga['name'], 'total': lga['total'],
                               'rows': [{'abbr': v['abbr'], 'votes': v['votes'], 'pct': v['pct'],
                                         'color': v['color']} for v in lga['votes']]}),
    } for i, lga in enumerate(lgas)]
    grid = [{'y': round(top_pad + plot_h - t / top * plot_h, 1), 'label': short(t)} for t in _ticks(top)]
    return {'width': width, 'height': height, 'series': series, 'columns': columns, 'grid': grid,
            'left': left, 'right': width - right, 'plot_top': top_pad, 'plot_bottom': top_pad + plot_h,
            'label_y': top_pad + plot_h + 12}
