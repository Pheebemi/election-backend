from django.test import TestCase, override_settings

from election.models import (
    ElectionResult, LocalGovernmentArea, PoliticalParty, PollingUnit, ResultChange, User, Ward, WardResult,
)


@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False)
class PortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user('chief', password='pw-123456!', role=User.ADMIN)
        cls.clerk = User.objects.create_user('clerk', password='pw-123456!')
        cls.jalingo = LocalGovernmentArea.objects.create(name='Jalingo', code='07')
        cls.wukari = LocalGovernmentArea.objects.create(name='Wukari', code='16')
        cls.clerk.assigned_lgas.add(cls.jalingo)
        cls.ward = Ward.objects.create(name='Barade', lga=cls.jalingo)
        cls.ward_w = Ward.objects.create(name='Puje', lga=cls.wukari)
        cls.pu = PollingUnit.objects.create(name='Barade Primary School', ward=cls.ward)
        cls.pu_w = PollingUnit.objects.create(name='Puje Market', ward=cls.ward_w)
        cls.apc = PoliticalParty.objects.create(name='All Progressives Congress', abbreviation='APC', color='#264b5e')
        cls.pdp = PoliticalParty.objects.create(name='Peoples Democratic Party', abbreviation='PDP', color='#f23d0e')
        ElectionResult.objects.create(polling_unit=cls.pu_w, party=cls.pdp, votes=40)

    def test_public_pages(self):
        for url in ['/', '/present/', '/login/']:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, url)
        r = self.client.get('/')
        self.assertContains(r, 'PDP leads')
        self.assertContains(r, 'Wukari')

    def test_dashboard_needs_login(self):
        for url in ['/dashboard/', '/dashboard/progress/', '/dashboard/reports/', '/print/lga/?id=1']:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertTrue(r['Location'].startswith('/login/'), url)

    def test_login_then_dashboard(self):
        r = self.client.post('/login/', {'username': 'clerk', 'password': 'pw-123456!'})
        self.assertRedirects(r, '/dashboard/', fetch_redirect_response=False)
        r = self.client.get('/dashboard/')
        self.assertContains(r, 'Barade Primary School')
        self.assertNotContains(r, 'Puje')  # not assigned to Wukari

    def test_clerk_saves_polling_unit_results(self):
        self.client.force_login(self.clerk)
        r = self.client.post('/dashboard/', {
            'lga': self.jalingo.id, 'ward': self.ward.id, 'pu': self.pu.id,
            f'party_{self.apc.id}': '120', f'party_{self.pdp.id}': '',
        })
        self.assertEqual(r.status_code, 302)
        votes = dict(ElectionResult.objects.filter(polling_unit=self.pu).values_list('party__abbreviation', 'votes'))
        self.assertEqual(votes, {'APC': 120, 'PDP': 0})
        change = ResultChange.objects.get(polling_unit=self.pu, party=self.apc)
        self.assertEqual(change.changed_by, self.clerk)

    def test_clerk_cannot_save_outside_assigned_lga(self):
        self.client.force_login(self.clerk)
        self.client.post('/dashboard/', {
            'lga': self.wukari.id, 'ward': self.ward_w.id, 'pu': self.pu_w.id, f'party_{self.apc.id}': '999',
        })
        self.assertFalse(ElectionResult.objects.filter(polling_unit=self.pu_w, party=self.apc).exists())

    def test_ward_override(self):
        self.client.force_login(self.admin)
        self.client.post('/dashboard/', {
            'mode': 'ward', 'lga': self.jalingo.id, 'ward': self.ward.id, f'party_{self.apc.id}': '500',
        })
        self.assertEqual(WardResult.objects.get(ward=self.ward, party=self.apc).votes, 500)

    def test_admin_pages_and_clerk_redirect(self):
        self.client.force_login(self.clerk)
        self.assertRedirects(self.client.get('/dashboard/clerks/'), '/dashboard/', fetch_redirect_response=False)
        self.assertRedirects(self.client.get('/dashboard/history/'), '/dashboard/', fetch_redirect_response=False)
        self.client.force_login(self.admin)
        for url in ['/dashboard/clerks/', '/dashboard/history/', '/dashboard/progress/',
                    f'/print/lga/?id={self.wukari.id}']:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_admin_creates_and_assigns_clerk(self):
        self.client.force_login(self.admin)
        r = self.client.post('/dashboard/clerks/', {
            'action': 'create', 'username': 'newbie', 'password': 'S3cure-pass-xyz', 'confirm': 'S3cure-pass-xyz',
            'lga_ids': [self.wukari.id],
        })
        self.assertEqual(r.status_code, 302)
        newbie = User.objects.get(username='newbie')
        self.assertEqual(list(newbie.assigned_lgas.all()), [self.wukari])
        self.client.post('/dashboard/clerks/', {'action': 'assign', 'clerk': newbie.id,
                                                'lga_ids': [self.jalingo.id, self.wukari.id]})
        self.assertEqual(newbie.assigned_lgas.count(), 2)

    def test_mismatched_passwords_rejected(self):
        self.client.force_login(self.admin)
        r = self.client.post('/dashboard/clerks/', {
            'action': 'create', 'username': 'x1', 'password': 'S3cure-pass-xyz', 'confirm': 'other-pass-xyz'})
        self.assertContains(r, 'Passwords do not match.')
        self.assertFalse(User.objects.filter(username='x1').exists())

    def test_exports(self):
        self.client.force_login(self.admin)
        r = self.client.get('/dashboard/reports/export.csv')
        self.assertEqual(r.status_code, 200)
        self.assertIn('Puje Market', r.content.decode())
        r = self.client.get('/dashboard/reports/export.xlsx')
        self.assertEqual(r.content[:2], b'PK')

    def test_api_still_served(self):
        self.assertEqual(self.client.get('/api/polling-units/stats/').status_code, 200)


def _png(size=(40, 40), colour=(200, 30, 30)):
    import io
    from PIL import Image
    out = io.BytesIO()
    Image.new('RGB', size, colour).save(out, 'PNG')
    return out.getvalue()


@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False)
class ElectionTests(TestCase):
    """Governorship and Presidential results are kept apart."""

    @classmethod
    def setUpTestData(cls):
        from election.models import Election
        cls.gov = Election.objects.get(slug='governorship')
        cls.pres = Election.objects.get(slug='presidential')
        cls.admin = User.objects.create_user('chief', password='pw-123456!', role=User.ADMIN)
        cls.clerk = User.objects.create_user('clerk', password='pw-123456!')
        cls.lga = LocalGovernmentArea.objects.create(name='Jalingo', code='07')
        cls.clerk.assigned_lgas.add(cls.lga)
        cls.ward = Ward.objects.create(name='Barade', lga=cls.lga)
        cls.pu = PollingUnit.objects.create(name='Barade Primary School', ward=cls.ward)
        cls.pu2 = PollingUnit.objects.create(name='Barade Market', ward=cls.ward)
        cls.apc = PoliticalParty.objects.create(name='All Progressives Congress', abbreviation='APC', color='#264b5e')
        cls.pdp = PoliticalParty.objects.create(name='Peoples Democratic Party', abbreviation='PDP', color='#f23d0e')

    def enter(self, election, apc, pdp, **extra):
        return self.client.post('/dashboard/', {
            'election': election, 'lga': self.lga.id, 'ward': self.ward.id, 'pu': self.pu.id,
            f'party_{self.apc.id}': str(apc), f'party_{self.pdp.id}': str(pdp), **extra})

    def test_elections_exist_and_results_default_to_governorship(self):
        r = ElectionResult.objects.create(polling_unit=self.pu, party=self.apc, votes=5)
        self.assertEqual(r.election, self.gov)

    def test_same_polling_unit_holds_a_result_for_each_election(self):
        self.client.force_login(self.clerk)
        self.enter('governorship', 100, 50)
        self.enter('presidential', 30, 90)
        gov = dict(ElectionResult.objects.filter(election=self.gov, polling_unit=self.pu)
                   .values_list('party__abbreviation', 'votes'))
        pres = dict(ElectionResult.objects.filter(election=self.pres, polling_unit=self.pu)
                    .values_list('party__abbreviation', 'votes'))
        self.assertEqual(gov, {'APC': 100, 'PDP': 50})
        self.assertEqual(pres, {'APC': 30, 'PDP': 90})
        # Saving again updates in place, not a second row.
        self.enter('presidential', 31, 91)
        self.assertEqual(ElectionResult.objects.filter(election=self.pres, polling_unit=self.pu).count(), 2)

    def test_public_page_defaults_to_governorship_and_switches(self):
        ElectionResult.objects.create(polling_unit=self.pu, party=self.apc, votes=100, election=self.gov)
        ElectionResult.objects.create(polling_unit=self.pu, party=self.pdp, votes=300, election=self.pres)
        r = self.client.get('/')
        self.assertContains(r, 'Live · Governorship')
        self.assertContains(r, 'APC leads')
        self.assertContains(r, '?election=presidential')           # the switch
        r = self.client.get('/?election=presidential')
        self.assertContains(r, 'Live · Presidential')
        self.assertContains(r, 'PDP leads')
        self.assertContains(self.client.get('/?election=nonsense'), 'Live · Governorship')  # unknown -> default

    def test_public_page_ignores_the_session(self):
        self.client.force_login(self.clerk)
        self.client.get('/dashboard/?election=presidential')
        self.assertContains(self.client.get('/'), 'Live · Governorship')

    def test_dashboard_remembers_the_chosen_election(self):
        self.client.force_login(self.clerk)
        self.assertContains(self.client.get('/dashboard/'), 'name="election" value="governorship"')
        self.client.get('/dashboard/?election=presidential')
        self.assertContains(self.client.get('/dashboard/progress/'), 'aria-current="true"')
        self.assertContains(self.client.get('/dashboard/'), 'name="election" value="presidential"')

    def test_progress_and_ticks_are_per_election(self):
        self.client.force_login(self.clerk)
        self.enter('governorship', 10, 10)
        r = self.client.get('/dashboard/?election=governorship')
        self.assertContains(r, '✓ Barade Primary School')
        r = self.client.get('/dashboard/?election=presidential')
        self.assertNotContains(r, '✓ Barade Primary School')
        prog = self.client.get('/dashboard/progress/?election=presidential').context['data']
        self.assertEqual(prog['overall']['reported'], 0)
        prog = self.client.get('/dashboard/progress/?election=governorship').context['data']
        self.assertEqual(prog['overall']['reported'], 1)

    def test_ward_override_is_per_election(self):
        self.client.force_login(self.admin)
        self.client.post('/dashboard/', {'election': 'presidential', 'mode': 'ward', 'lga': self.lga.id,
                                         'ward': self.ward.id, f'party_{self.apc.id}': '700'})
        self.assertEqual(WardResult.objects.get(ward=self.ward, party=self.apc).election, self.pres)
        gov = self.client.get('/?election=governorship').context['board']
        pres = self.client.get('/?election=presidential').context['board']
        self.assertEqual(gov['grand_total'], 0)
        self.assertEqual(pres['grand_total'], 700)

    def test_history_and_exports_are_per_election(self):
        self.client.force_login(self.admin)
        self.enter('governorship', 1, 1)
        self.enter('presidential', 2, 2)
        self.assertEqual(ResultChange.objects.filter(election=self.gov).count(), 2)
        self.assertEqual(ResultChange.objects.filter(election=self.pres).count(), 2)
        page = self.client.get('/dashboard/history/?election=presidential')
        self.assertEqual(len(page.context['page_obj']), 2)
        r = self.client.get('/dashboard/reports/export.csv?election=presidential')
        self.assertIn('presidential', r['Content-Disposition'])
        r = self.client.get('/dashboard/reports/export.csv?election=governorship')
        self.assertIn('governorship', r['Content-Disposition'])

    def test_api_takes_an_election(self):
        ElectionResult.objects.create(polling_unit=self.pu, party=self.apc, votes=100, election=self.gov)
        ElectionResult.objects.create(polling_unit=self.pu, party=self.apc, votes=900, election=self.pres)
        gov = self.client.get('/api/results/chart_data/').json()
        pres = self.client.get('/api/results/chart_data/?election=presidential').json()
        self.assertEqual({r['party']: r['votes'] for r in gov['radial']}['APC'], 100)
        self.assertEqual({r['party']: r['votes'] for r in pres['radial']}['APC'], 900)


@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False)
class PartyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user('chief', password='pw-123456!', role=User.ADMIN)
        cls.clerk = User.objects.create_user('clerk', password='pw-123456!')
        cls.apc = PoliticalParty.objects.create(name='All Progressives Congress', abbreviation='APC', color='#264b5e')
        cls.lga = LocalGovernmentArea.objects.create(name='Jalingo', code='07')
        cls.ward = Ward.objects.create(name='Barade', lga=cls.lga)
        cls.pu = PollingUnit.objects.create(name='Barade Primary School', ward=cls.ward)

    def add(self, **over):
        from django.core.files.uploadedfile import SimpleUploadedFile
        data = {'action': 'create', 'name': 'Labour Party', 'abbreviation': 'lp', 'color': '#ff0000', **over}
        if 'logo' not in over:
            data['logo'] = SimpleUploadedFile('lp.png', _png(), content_type='image/png')
        return self.client.post('/dashboard/parties/', data)

    def test_only_admins_manage_parties(self):
        self.client.force_login(self.clerk)
        self.assertRedirects(self.client.get('/dashboard/parties/'), '/dashboard/', fetch_redirect_response=False)
        self.add()
        self.assertFalse(PoliticalParty.objects.filter(abbreviation='LP').exists())

    def test_admin_adds_a_party_with_a_logo_and_it_shows_up_everywhere(self):
        self.client.force_login(self.admin)
        r = self.add()
        self.assertRedirects(r, '/dashboard/parties/', fetch_redirect_response=False)
        lp = PoliticalParty.objects.get(abbreviation='LP')
        self.assertEqual((lp.name, lp.color), ('Labour Party', '#ff0000'))
        self.assertTrue(lp.logo_data)
        logo = self.client.get(f'/party-logo/{lp.pk}/')
        self.assertEqual((logo.status_code, logo['Content-Type']), (200, 'image/png'))
        self.client.logout()
        self.assertEqual(self.client.get(f'/party-logo/{lp.pk}/').status_code, 200)   # public scoreboard needs it
        self.client.force_login(self.admin)
        page = self.client.get('/dashboard/?election=presidential')
        self.assertContains(page, f'party_{lp.id}')            # on the entry form for both elections
        self.assertContains(self.client.get('/dashboard/?election=governorship'), f'party_{lp.id}')

    def test_party_without_a_logo_gets_a_coloured_badge(self):
        self.client.force_login(self.admin)
        self.add(logo='')
        lp = PoliticalParty.objects.get(abbreviation='LP')
        self.assertIsNone(lp.logo_url)
        self.assertEqual(self.client.get(f'/party-logo/{lp.pk}/').status_code, 404)

    def test_validation(self):
        self.client.force_login(self.admin)
        r = self.add(name='All Progressives Congress', abbreviation='APC', color='nope')
        for text in ('Pick a colour.', 'already exists'):
            self.assertContains(r, text)
        r = self.add(logo=__import__('django.core.files.uploadedfile', fromlist=['x']).SimpleUploadedFile(
            'x.png', b'<html>not an image</html>', content_type='image/png'))
        self.assertContains(r, 'must be a PNG, JPG or WEBP picture')
        self.assertEqual(PoliticalParty.objects.count(), 1)

    def test_update_and_delete_rules(self):
        self.client.force_login(self.admin)
        self.add()
        lp = PoliticalParty.objects.get(abbreviation='LP')
        self.client.post('/dashboard/parties/', {'action': 'update', 'party': lp.pk, 'name': 'Labour', 'abbreviation': 'LAB',
                                                 'color': '#00ff00', 'remove_logo': '1'})
        lp.refresh_from_db()
        self.assertEqual((lp.name, lp.abbreviation, lp.color, bool(lp.logo_data)), ('Labour', 'LAB', '#00ff00', False))
        ElectionResult.objects.create(polling_unit=self.pu, party=self.apc, votes=3)
        self.client.post('/dashboard/parties/', {'action': 'delete', 'party': self.apc.pk})
        self.assertTrue(PoliticalParty.objects.filter(pk=self.apc.pk).exists())     # has results: kept
        self.client.post('/dashboard/parties/', {'action': 'delete', 'party': lp.pk})
        self.assertFalse(PoliticalParty.objects.filter(pk=lp.pk).exists())
