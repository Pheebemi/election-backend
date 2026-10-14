"""Data for the web pages, taken from the existing API views.

The pages call the same DRF actions the old Next.js frontend called (stats,
chart data, progress, exports ...), in-process, so the numbers on screen are
computed in exactly one place. Only the main dataset is shown on the web
portal; the API keeps serving other datasets (e.g. apc) to other frontends.
"""
import copy
import json
from functools import lru_cache
from pathlib import Path

from django.http import Http404, QueryDict
from django.core.exceptions import PermissionDenied

from election.views import (
    ClerkViewSet, ElectionResultViewSet, PollingUnitViewSet, ResultChangeViewSet,
)
from election.models import PoliticalParty

MAP_FILE = Path(__file__).resolve().parent / 'data' / 'taraba_map.json'
NO_DATA = 'rgba(148,163,184,0.30)'
DATASET = 'main'


def call(request, viewset, action, **params):
    """Run ``viewset``'s GET ``action`` as the current user and return its data."""
    sub = copy.copy(request)
    sub.method = 'GET'
    query = QueryDict(mutable=True)
    for key, value in params.items():
        if value not in (None, ''):
            query[key] = str(value)
    sub.GET = query
    # The web portal always shows the main dataset, whatever the browser sends.
    sub.META = {**request.META, 'QUERY_STRING': query.urlencode(), 'HTTP_X_DATASET': DATASET}
    # Like the router: an @action's own settings (e.g. AllowAny) apply.
    view = viewset.as_view({'get': action}, **getattr(getattr(viewset, action), 'kwargs', {}))
    response = view(sub)
    if response.status_code == 404:
        raise Http404
    if response.status_code in (401, 403):
        raise PermissionDenied
    return response.data


def stats(request):
    return call(request, PollingUnitViewSet, 'stats')


def chart_data(request):
    return call(request, ElectionResultViewSet, 'chart_data')


def latest(request, limit=20):
    return call(request, PollingUnitViewSet, 'latest', limit=limit)


def progress(request):
    return call(request, PollingUnitViewSet, 'progress')


def recent_entries(request, page=1):
    return call(request, PollingUnitViewSet, 'recent_entries', page=page)


def export(request, lga=None, ward=None):
    return call(request, ElectionResultViewSet, 'export', lga=lga, ward=ward)


def lga_report(request, lga):
    return call(request, ElectionResultViewSet, 'lga_report', lga=lga)


def history(request, **filters):
    return call(request, ResultChangeViewSet, 'list', **filters)


def clerks(request):
    return call(request, ClerkViewSet, 'list')


# ---------------------------------------------------------------------------
# Shaping chart data for templates
# ---------------------------------------------------------------------------

def parties_config():
    """Every party, in the API's order, with colour and logo."""
    return [
        {'abbr': p.abbreviation, 'name': p.name, 'color': p.color or '#64748b', 'logo': p.logo_url}
        for p in PoliticalParty.objects.all()
    ]


def percent(part, whole):
    """Share as a 0-100 number for CSS widths, capped at 100."""
    return min(100.0, round(part / whole * 100, 1)) if whole else 0.0


def results_board(request):
    """Everything the live results page and projector need."""
    chart = chart_data(request)
    parties = parties_config()
    by_abbr = {p['abbr']: p for p in parties}
    st = stats(request)

    totals = sorted(
        ({**by_abbr[r['party']], 'votes': r['votes']} for r in chart['radial'] if r['party'] in by_abbr),
        key=lambda r: -r['votes'],
    )
    grand = sum(r['votes'] for r in totals)
    for r in totals:
        r['pct'] = round(r['votes'] / grand * 100, 1) if grand else 0.0

    reported = {l['lga']: l for l in st['by_lga']}
    lgas = []
    for row in chart['bar']:
        votes = sorted(
            ({**p, 'votes': int(row.get(p['abbr'], 0) or 0)} for p in parties), key=lambda r: -r['votes'])
        total = sum(v['votes'] for v in votes)
        top = max((v['votes'] for v in votes), default=0) or 1
        for v in votes:
            v['pct'] = round(v['votes'] / total * 100, 1) if total else 0.0
            v['bar'] = round(v['votes'] / top * 100, 1)
        s = reported.get(row['lga'], {})
        lgas.append({
            'name': row['lga'], 'total': total, 'votes': votes,
            'winner': votes[0] if total else None,
            'reported': s.get('reported_polling_units', 0), 'polling_units': s.get('polling_units', 0),
            'reported_pct': percent(s.get('reported_polling_units', 0), s.get('polling_units', 0)),
        })
    top_party = totals[0]['votes'] if totals else 0
    for r in totals:
        r['bar'] = round(r['votes'] / top_party * 100, 1) if top_party else 0
    return {
        'parties': parties,
        'totals': totals,
        'grand_total': grand,
        'leader': totals[0] if grand else None,
        'runner_up': totals[1] if grand and len(totals) > 1 else None,
        'lead': (totals[0]['votes'] - totals[1]['votes']) if grand and len(totals) > 1 else 0,
        'lgas': lgas,
        'stats': st,
        'bar_rows': chart['bar'],
    }


# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _map_data():
    with open(MAP_FILE, encoding='utf-8') as f:
        return json.load(f)


def normalize(name):
    return ' '.join((name or '').lower().replace('-', ' ').split())


def state_map(lgas):
    """SVG shapes for the 16 LGAs, filled with the leading party's colour."""
    data = _map_data()
    by_key = {normalize(l['name']): l for l in lgas}
    shapes = []
    for s in data['lgas']:
        lga = by_key.get(s['key'])
        winner = lga['winner'] if lga else None
        shapes.append({
            'd': s['d'], 'cx': s['cx'], 'cy': s['cy'], 'key': s['key'],
            'name': lga['name'] if lga else s['name'],
            'fill': winner['color'] if winner else NO_DATA,
            'label': winner['abbr'] if winner else '',
            'total': lga['total'] if lga else 0,
            'breakdown': [{'abbr': v['abbr'], 'votes': v['votes'], 'pct': v['pct'], 'color': v['color']}
                          for v in (lga['votes'] if lga else [])],
        })
    for s in shapes:
        s['tooltip'] = json.dumps({'name': s['name'], 'winner': s['label'], 'total': s['total'],
                                   'rows': s['breakdown']})
    winners = []
    for s in shapes:
        if s['label'] and s['label'] not in [w['abbr'] for w in winners]:
            winners.append({'abbr': s['label'], 'color': s['fill']})
    return {'shapes': shapes, 'viewbox': f"0 0 {data['width']} {data['height']}", 'winners': winners,
            'count': len(shapes)}


def polling_units(ward):
    """A ward's polling units, ticked when they have results."""
    from django.db.models import Exists, OuterRef
    from election.models import ElectionResult, PollingUnit
    return PollingUnit.objects.filter(ward=ward).order_by('name').annotate(
        has_results=Exists(ElectionResult.objects.filter(polling_unit=OuterRef('pk'))))
