"""Pages of the election portal: the public results, projector and print
sheet, and the clerk/admin dashboard. Numbers come from the API views (see
services.py); saving results and managing clerks use the same rules as the API.
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
import io
import re

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from django.views.decorators.http import require_http_methods

from election.models import (
    Election, ElectionResult, LocalGovernmentArea, PoliticalParty, PollingUnit, ResultChange, User, Ward, WardResult,
    default_election,
)
from election.views import visible_lga_ids

from . import charts, exports, services
from .services import DATASET, percent

NAV = [
    ('web:entry', 'Enter results', 'pen-square', False),
    ('web:progress', 'Progress', 'clipboard-list', False),
    ('web:reports', 'Reports', 'file-spreadsheet', False),
    ('web:history', 'Change history', 'history', True),
    ('web:clerks', 'Clerks', 'users', True),
    ('web:parties', 'Parties', 'flag', True),
]


def admin_required(view):
    """Signed-in admins only; clerks are sent back to the entry page."""
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_admin:
            return redirect('web:entry')
        return view(request, *args, **kwargs)
    return wrapped


def dash(request, template, title, current, **context):
    nav = [
        {'url': reverse(name), 'label': label, 'icon': icon, 'active': name == current}
        for name, label, icon, admin_only in NAV if not admin_only or request.user.is_admin
    ]
    return render(request, template, {'page_title': title, 'nav': nav, **context})


def current_election(request, remember=False):
    """The election this page is about: ``?election=<slug>``, else (signed-in pages) the one the
    person chose last, else Governorship. Public pages never use the session, so a link
    without ``?election=`` always means Governorship."""
    slug = request.POST.get('election') or request.GET.get('election')
    if not slug and remember:
        slug = request.session.get('election')
    election = Election.objects.filter(slug=slug).first() or Election.objects.get(pk=default_election())
    if remember:
        request.session['election'] = election.slug
    request.election, request.election_slug = election, election.slug
    return election


def user_lgas(user):
    lgas = LocalGovernmentArea.objects.filter(dataset=DATASET).order_by('name')
    ids = visible_lga_ids(user)
    return lgas if ids is None else lgas.filter(id__in=ids)


def pick(queryset, value):
    """The object in ``queryset`` with id ``value``, else the first one."""
    if value and str(value).isdigit():
        found = queryset.filter(id=value).first()
        if found:
            return found
    return queryset.first()


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------

def home(request):
    current_election(request)
    board = services.results_board(request)
    st = board['stats']
    return render(request, 'web/home.html', {
        'board': board,
        'map': services.state_map(board['lgas']),
        'bars': charts.stacked_bars(board['lgas'], board['parties']),
        'radial': charts.radial(board['totals']),
        'lines': charts.lines(board['lgas'], board['parties']),
        'reported_bar': min(st['reported_percent'], 100),
        'coverage': [
            {'label': 'Polling units', 'value': st['total_polling_units']},
            {'label': 'Wards', 'value': st['total_wards']},
            {'label': 'Local Governments', 'value': st['total_lgas']},
        ],
    })


def present(request):
    current_election(request)
    board = services.results_board(request)
    latest = services.latest(request, limit=20)
    return render(request, 'web/present.html', {
        'board': board,
        'map': services.state_map(board['lgas']),
        'latest': latest,
        'ticker_seconds': max(30, len(latest) * 6),
    })


class LoginView(auth_views.LoginView):
    template_name = 'web/login.html'
    redirect_authenticated_user = True


@login_required
def print_lga(request):
    current_election(request, remember=True)
    report = services.lga_report(request, request.GET.get('id'))
    parties = report['parties']
    totals = report['totals']
    total = report['total_votes']
    ranked = sorted(parties, key=lambda p: -totals.get(p['abbreviation'], 0))
    leader = ranked[0] if total else None
    runner_up = ranked[1] if total and len(ranked) > 1 else None
    top = totals.get(leader['abbreviation'], 0) if leader else 0
    for p in ranked:
        v = totals.get(p['abbreviation'], 0)
        p.update(votes=v, bar=percent(v, top), pct=round(v / total * 100, 1) if total else 0.0)
    wards = []
    for w in report['wards']:
        best = max(parties, key=lambda p: w['votes'].get(p['abbreviation'], 0)) if w['total'] else None
        wards.append({**w, 'leader': best, 'cells': [w['votes'].get(p['abbreviation'], 0) for p in parties]})
    return render(request, 'web/print_lga.html', {
        'report': report, 'ranked': ranked, 'leader': leader, 'runner_up': runner_up,
        'margin': totals[leader['abbreviation']] - totals[runner_up['abbreviation']] if runner_up else 0,
        'wards': wards, 'total_cells': [totals.get(p['abbreviation'], 0) for p in parties],
        'any_override': any(w['override'] for w in report['wards']),
        'reported_pct': percent(report['reported'], report['polling_units']),
        'signoff': ['Prepared by', 'Checked by', 'Date and time'],
    })


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(['GET', 'POST'])
def entry(request):
    election = current_election(request, remember=True)
    data = request.POST if request.method == 'POST' else request.GET
    override = data.get('mode') == 'ward'
    lgas = user_lgas(request.user)
    lga = pick(lgas, data.get('lga'))
    wards = Ward.objects.filter(lga=lga).order_by('name') if lga else Ward.objects.none()
    ward = pick(wards, data.get('ward'))
    units = list(services.polling_units(ward, election)) if ward else []
    pu = next((u for u in units if str(u.id) == str(data.get('pu'))), units[0] if units else None)
    parties = list(PoliticalParty.objects.all())

    if request.method == 'POST':
        target = ward if override else pu
        if target is None:
            messages.error(request, 'Please select a ward' if override else 'Please select a polling unit')
        else:
            votes = {}
            for party in parties:
                raw = (request.POST.get(f'party_{party.id}') or '').strip()
                try:
                    votes[party] = max(0, int(raw or 0))
                except ValueError:
                    messages.error(request, f'Votes for {party.abbreviation} must be a whole number.')
                    break
            else:
                model, field = (WardResult, 'ward') if override else (ElectionResult, 'polling_unit')
                with transaction.atomic():
                    for party, v in votes.items():
                        model.objects.update_or_create(
                            **{field: target, 'party': party, 'election': election},
                            defaults={'votes': v, 'entered_by': request.user},
                        )
                messages.success(request, 'Results saved successfully!')
        query = {'lga': lga.id if lga else '', 'ward': ward.id if ward else '', 'pu': pu.id if pu else '',
                 'election': election.slug}
        if override:
            query['mode'] = 'ward'
        return redirect(f"{reverse('web:entry')}?{urlencode(query)}")

    if override and ward:
        existing = dict(WardResult.objects.filter(election=election, ward=ward).values_list('party_id', 'votes'))
    elif pu:
        existing = dict(ElectionResult.objects.filter(election=election, polling_unit=pu).values_list('party_id', 'votes'))
    else:
        existing = {}
    reported = sum(1 for u in units if u.has_results)
    return dash(request, 'web/dash/entry.html', 'Enter results', 'web:entry',
                lgas=lgas, lga=lga, wards=wards, ward=ward, units=units, pu=pu, parties=parties,
                mode='ward' if override else 'pu', mode_override=override,
                existing=existing, existing_total=sum(existing.values()),
                can_save=bool(ward if override else pu),
                units_reported=reported, units_pct=round(reported / len(units) * 100) if units else 0)


@login_required
def progress(request):
    current_election(request, remember=True)
    data = services.progress(request)
    recent = None
    if data.get('is_admin'):
        recent = services.recent_entries(request, page=request.GET.get('page') or 1)
    return dash(request, 'web/dash/progress.html', 'Entry progress', 'web:progress',
                data=data, recent=recent,
                lgas_complete=sum(1 for l in data['by_lga'] if l['total'] > 0 and l['reported'] >= l['total']))


def _report_scope(request):
    lgas = user_lgas(request.user)
    lga = lgas.filter(id=request.GET.get('lga')).first() if (request.GET.get('lga') or '').isdigit() else None
    wards = Ward.objects.filter(lga=lga).order_by('name') if lga else Ward.objects.none()
    ward = wards.filter(id=request.GET.get('ward')).first() if lga and (request.GET.get('ward') or '').isdigit() else None
    scope = f'{lga.name} {ward.name} ward' if ward else lga.name if lga else 'Taraba State'
    return lgas, lga, wards, ward, scope


@login_required
def reports(request):
    current_election(request, remember=True)
    lgas, lga, wards, ward, scope = _report_scope(request)
    query = urlencode({k: v for k, v in (('lga', lga and lga.id), ('ward', ward and ward.id)) if v})
    return dash(request, 'web/dash/reports.html', 'Reports & downloads', 'web:reports',
                lgas=lgas, lga=lga, wards=wards, ward=ward, scope=scope, query=query)


@login_required
def export(request, fmt):
    election = current_election(request, remember=True)
    _lgas, lga, _wards, ward, scope = _report_scope(request)
    data = services.export(request, lga=lga and lga.id, ward=ward and ward.id)
    if fmt == 'xlsx':
        response = HttpResponse(
            exports.excel(data),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    elif fmt == 'csv':
        response = HttpResponse(exports.csv_text(data), content_type='text/csv; charset=utf-8')
    else:
        raise Http404
    name = exports.file_name(election.name + ' ' + scope, fmt)
    response['Content-Disposition'] = f'attachment; filename="{name}"'
    return response


@admin_required
def history(request):
    election = current_election(request, remember=True)
    qs = (ResultChange.objects.filter(dataset=DATASET, election=election)
          .select_related('lga', 'ward', 'polling_unit'))
    unit = None
    filters = {}
    if (request.GET.get('polling_unit') or '').isdigit():
        unit = PollingUnit.objects.filter(id=request.GET['polling_unit'], dataset=DATASET).first()
        qs = qs.filter(polling_unit_id=request.GET['polling_unit'])
        filters['polling_unit'] = request.GET['polling_unit']
    else:
        if (request.GET.get('lga') or '').isdigit():
            qs = qs.filter(lga_id=request.GET['lga'])
            filters['lga'] = request.GET['lga']
        if request.GET.get('kind') in (ResultChange.POLLING_UNIT, ResultChange.WARD):
            qs = qs.filter(kind=request.GET['kind'])
            filters['kind'] = request.GET['kind']
    paginator = Paginator(qs, 100)
    page_obj = paginator.get_page(request.GET.get('page'))
    for row in page_obj:
        row.delta = (row.new_votes or 0) - (row.old_votes or 0)
    return dash(request, 'web/dash/history.html', 'Change history', 'web:history',
                page_obj=page_obj, paginator=paginator, unit=unit,
                lgas=user_lgas(request.user), lga_id=int(filters['lga']) if 'lga' in filters else None,
                kind=filters.get('kind', ''), base_query=urlencode(filters) + '&' if filters else '')


@admin_required
@require_http_methods(['GET', 'POST'])
def clerks(request):
    lgas = list(user_lgas(request.user))
    lga_ids = {l.id for l in lgas}
    form_errors, form_data, saved = [], {'lga_ids': set()}, None

    if request.method == 'POST':
        chosen = {int(i) for i in request.POST.getlist('lga_ids') if i.isdigit() and int(i) in lga_ids}
        if request.POST.get('action') == 'assign':
            clerk = get_object_or_404(User, pk=request.POST.get('clerk'), role=User.CLERK)
            # Keep any assignments the clerk has in other datasets untouched.
            keep = list(clerk.assigned_lgas.exclude(dataset=DATASET))
            clerk.assigned_lgas.set(keep + [l for l in lgas if l.id in chosen])
            return redirect(f"{reverse('web:clerks')}?saved={clerk.id}#clerk-{clerk.id}")

        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''
        form_data = {'username': username, 'first_name': (request.POST.get('first_name') or '').strip(),
                     'last_name': (request.POST.get('last_name') or '').strip(), 'lga_ids': chosen}
        if not username:
            form_errors.append('Username is required.')
        elif User.objects.filter(username__iexact=username).exists():
            form_errors.append('A user with that username already exists.')
        if password != request.POST.get('confirm'):
            form_errors.append('Passwords do not match.')
        candidate = User(username=username, first_name=form_data['first_name'],
                         last_name=form_data['last_name'], role=User.CLERK)
        try:
            validate_password(password, user=candidate)
        except ValidationError as exc:
            form_errors.extend(exc.messages)
        if not form_errors:
            candidate.set_password(password)
            candidate.save()
            candidate.assigned_lgas.set([l for l in lgas if l.id in chosen])
            messages.success(request, f'Clerk "{username}" created.')
            return redirect('web:clerks')

    names = {l.id: l.name for l in lgas}
    rows = services.clerks(request)
    for c in rows:
        c['assigned_lga_ids'] = set(c['assigned_lga_ids'])
        c['assigned_names'] = sorted(names[i] for i in c['assigned_lga_ids'] if i in names)
    saved = int(request.GET['saved']) if (request.GET.get('saved') or '').isdigit() else None
    return dash(request, 'web/dash/clerks.html', 'Clerk assignments', 'web:clerks',
                lgas=lgas, clerks=rows, form_errors=form_errors, form_data=form_data, saved=saved)


# ---------------------------------------------------------------------------
# Parties (admins add and edit them here; both elections share them)
# ---------------------------------------------------------------------------

HEX_COLOUR = re.compile(r'^#[0-9a-fA-F]{6}$')
MAX_LOGO_BYTES = 2 * 1024 * 1024


def read_logo(upload):
    """A party logo as (PNG bytes, 'image/png'), shrunk to fit 256 px; ValueError says what is wrong."""
    if upload.size > MAX_LOGO_BYTES:
        raise ValueError('The logo is too large (2 MB at most).')
    from PIL import Image
    try:
        image = Image.open(upload)
        image.load()
    except Exception:
        raise ValueError('The logo must be a PNG, JPG or WEBP picture.')
    if image.format not in ('PNG', 'JPEG', 'WEBP'):
        raise ValueError('The logo must be a PNG, JPG or WEBP picture.')
    image = image.convert('RGBA')
    image.thumbnail((256, 256))
    out = io.BytesIO()
    image.save(out, 'PNG', optimize=True)
    return out.getvalue(), 'image/png'


def party_logo(request, pk):
    """A party's stored logo (public: it appears on the public scoreboard)."""
    party = get_object_or_404(PoliticalParty, pk=pk)
    if not party.logo_data:
        raise Http404
    response = HttpResponse(bytes(party.logo_data), content_type=party.logo_type or 'image/png')
    response['Cache-Control'] = 'public, max-age=86400'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


def party_form_errors(request, party=None):
    """Clean the submitted party fields; returns (values, errors)."""
    name = ' '.join((request.POST.get('name') or '').split())
    abbr = (request.POST.get('abbreviation') or '').strip().upper()
    colour = (request.POST.get('color') or '').strip()
    errors = []
    if not name:
        errors.append('The party name is required.')
    if not abbr:
        errors.append('The abbreviation is required.')
    if not HEX_COLOUR.match(colour):
        errors.append('Pick a colour.')
    others = PoliticalParty.objects.exclude(pk=party.pk) if party else PoliticalParty.objects.all()
    if name and others.filter(name__iexact=name).exists():
        errors.append('A party with that name already exists.')
    if abbr and others.filter(abbreviation__iexact=abbr).exists():
        errors.append('A party with that abbreviation already exists.')
    if len(abbr) > 20:
        errors.append('The abbreviation is too long (20 characters at most).')
    return {'name': name, 'abbreviation': abbr, 'color': colour}, errors


@admin_required
@require_http_methods(['GET', 'POST'])
def parties(request):
    errors, form = [], {'color': '#1d6fb8'}
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete':
            party = get_object_or_404(PoliticalParty, pk=request.POST.get('party'))
            if ElectionResult.objects.filter(party=party).exists() or WardResult.objects.filter(party=party).exists():
                messages.error(request, f'{party.abbreviation} has results, so it cannot be deleted.')
            else:
                party.delete()
                messages.success(request, f'Deleted {party.abbreviation}.')
            return redirect('web:parties')
        party = get_object_or_404(PoliticalParty, pk=request.POST.get('party')) if action == 'update' else None
        values, errors = party_form_errors(request, party)
        logo = request.FILES.get('logo')
        logo_bytes = None
        if logo and not errors:
            try:
                logo_bytes = read_logo(logo)
            except ValueError as exc:
                errors.append(str(exc))
        if not errors:
            party = party or PoliticalParty()
            for key, value in values.items():
                setattr(party, key, value)
            if logo_bytes:
                party.logo_data, party.logo_type = logo_bytes
                party.logo = None
            if request.POST.get('remove_logo'):
                party.logo_data, party.logo_type, party.logo = None, '', None
            party.save()
            messages.success(request, f'{"Updated" if action == "update" else "Added"} {party.abbreviation}.')
            return redirect('web:parties')
        form = values
        if action == 'update':
            messages.error(request, ' '.join(errors))
            return redirect('web:parties')
    rows = []
    for party in PoliticalParty.objects.all():
        n = ElectionResult.objects.filter(party=party).count() + WardResult.objects.filter(party=party).count()
        rows.append({'party': party, 'logo': party.logo_url, 'results': n})
    return dash(request, 'web/dash/parties.html', 'Parties', 'web:parties', rows=rows, errors=errors, form=form)
