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
