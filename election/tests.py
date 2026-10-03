from rest_framework.test import APITestCase

from .models import LocalGovernmentArea, User


class ClerkCreateTests(APITestCase):
    url = '/api/clerks/'

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user('chief', password='pw-123456!', role=User.ADMIN)
        cls.clerk = User.objects.create_user('existing', password='pw-123456!')
        cls.jalingo = LocalGovernmentArea.objects.create(name='Jalingo', code='JAL')
        cls.apc_jalingo = LocalGovernmentArea.objects.create(name='Jalingo', code='JAL', dataset='apc')

    def test_admin_creates_clerk_with_lgas(self):
        self.client.force_authenticate(self.admin)
        r = self.client.post(self.url, {
            'username': 'newclerk', 'password': 'S3cure-pass-xyz', 'first_name': 'Ada',
            'lga_ids': [self.jalingo.id],
        }, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        clerk = User.objects.get(username='newclerk')
        self.assertEqual(clerk.role, User.CLERK)
        self.assertTrue(clerk.check_password('S3cure-pass-xyz'))
        self.assertEqual(r.data['assigned_lga_ids'], [self.jalingo.id])

    def test_lgas_from_other_dataset_are_ignored(self):
        self.client.force_authenticate(self.admin)
        r = self.client.post(self.url, {
            'username': 'mainclerk', 'password': 'S3cure-pass-xyz', 'lga_ids': [self.apc_jalingo.id],
        }, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['assigned_lga_ids'], [])

    def test_duplicate_username_and_weak_password_rejected(self):
        self.client.force_authenticate(self.admin)
        r = self.client.post(self.url, {'username': 'Existing', 'password': '123'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('username', r.data)
        self.assertIn('password', r.data)

    def test_clerks_cannot_create_clerks(self):
        self.client.force_authenticate(self.clerk)
        r = self.client.post(self.url, {'username': 'sneaky', 'password': 'S3cure-pass-xyz'}, format='json')
        self.assertEqual(r.status_code, 403)
        self.assertFalse(User.objects.filter(username='sneaky').exists())


class PollingUnitHasResultsTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from .models import ElectionResult, PoliticalParty, PollingUnit, Ward
        cls.admin = User.objects.create_user('chief', password='pw-123456!', role=User.ADMIN)
        lga = LocalGovernmentArea.objects.create(name='Jalingo', code='JAL')
        cls.ward = Ward.objects.create(name='Barade', lga=lga)
        cls.done = PollingUnit.objects.create(name='PU 1', ward=cls.ward)
        cls.todo = PollingUnit.objects.create(name='PU 2', ward=cls.ward)
        party = PoliticalParty.objects.create(name='All Progressives Congress', abbreviation='APC')
        ElectionResult.objects.create(polling_unit=cls.done, party=party, votes=10)

    def test_ward_list_flags_reported_units(self):
        self.client.force_authenticate(self.admin)
        r = self.client.get('/api/polling-units/', {'ward': self.ward.id})
        rows = r.data['results'] if isinstance(r.data, dict) else r.data
        self.assertEqual({row['name']: row['has_results'] for row in rows}, {'PU 1': True, 'PU 2': False})


class ResultsFixture(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from .models import PoliticalParty, PollingUnit, Ward
        cls.admin = User.objects.create_user('chief', password='pw-123456!', role=User.ADMIN)
        cls.clerk = User.objects.create_user('jclerk', password='pw-123456!')
        cls.jalingo = LocalGovernmentArea.objects.create(name='Jalingo', code='JAL')
        cls.wukari = LocalGovernmentArea.objects.create(name='Wukari', code='WUK')
        cls.clerk.assigned_lgas.set([cls.jalingo])
        cls.ward = Ward.objects.create(name='Barade', lga=cls.jalingo)
        cls.w_ward = Ward.objects.create(name='Puje', lga=cls.wukari)
        cls.pu1 = PollingUnit.objects.create(name='PU 1', code='34-07-01-001', ward=cls.ward)
        cls.pu2 = PollingUnit.objects.create(name='PU 2', code='34-07-01-002', ward=cls.ward)
        cls.w_pu = PollingUnit.objects.create(name='W PU', code='34-16-01-001', ward=cls.w_ward)
        cls.apc = PoliticalParty.objects.create(name='All Progressives Congress', abbreviation='APC')
        cls.pdp = PoliticalParty.objects.create(name='Peoples Democratic Party', abbreviation='PDP')

    def submit(self, user, pu, apc, pdp):
        self.client.force_authenticate(user)
        return self.client.post('/api/results/bulk_create/', {
            'polling_unit_id': pu.id,
            'results': [{'party_id': self.apc.id, 'votes': apc}, {'party_id': self.pdp.id, 'votes': pdp}],
        }, format='json')


class ResultHistoryTests(ResultsFixture):
    def test_first_entry_then_change_is_recorded(self):
        from .models import ResultChange
        self.submit(self.clerk, self.pu1, 100, 50)
        self.submit(self.clerk, self.pu1, 120, 50)   # APC changed, PDP unchanged
        rows = list(ResultChange.objects.order_by('id').values_list('party_abbreviation', 'action', 'old_votes', 'new_votes', 'changed_by_name'))
        self.assertEqual(rows, [
            ('APC', 'created', None, 100, 'jclerk'),
            ('PDP', 'created', None, 50, 'jclerk'),
            ('APC', 'updated', 100, 120, 'jclerk'),
        ])

    def test_ward_override_is_recorded(self):
        from .models import ResultChange
        self.client.force_authenticate(self.clerk)
        self.client.post('/api/ward-results/bulk_create/', {
            'ward_id': self.ward.id, 'results': [{'party_id': self.apc.id, 'votes': 900}],
        }, format='json')
        change = ResultChange.objects.get()
        self.assertEqual((change.kind, change.new_votes), ('ward', 900))
        self.assertIn('override', change.place)

    def test_history_endpoint_is_admin_only_and_filters(self):
        self.submit(self.clerk, self.pu1, 10, 5)
        self.submit(self.admin, self.pu1, 11, 5)
        self.client.force_authenticate(self.clerk)
        self.assertEqual(self.client.get('/api/result-history/').status_code, 403)
        self.client.force_authenticate(self.admin)
        r = self.client.get('/api/result-history/', {'polling_unit': self.pu1.id})
        rows = r.data['results']
        self.assertEqual(rows[0]['action'], 'updated')          # newest first
        self.assertEqual((rows[0]['old_votes'], rows[0]['new_votes'], rows[0]['changed_by_name']), (10, 11, 'chief'))
        self.assertEqual(self.client.get('/api/result-history/', {'lga': self.wukari.id}).data['count'], 0)


class TickerAndReportTests(ResultsFixture):
    def test_latest_is_public_and_hides_clerks(self):
        self.submit(self.clerk, self.pu1, 10, 5)
        self.client.force_authenticate(None)
        r = self.client.get('/api/polling-units/latest/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data[0]['polling_unit'], 'PU 1')
        self.assertEqual(r.data[0]['ward'], 'Barade')
        self.assertNotIn('jclerk', str(r.data))

    def test_stats_report_polling_units_per_lga(self):
        self.submit(self.clerk, self.pu1, 10, 5)
        r = self.client.get('/api/polling-units/stats/')
        by = {row['lga']: row['reported_polling_units'] for row in r.data['by_lga']}
        self.assertEqual(by, {'Jalingo': 1, 'Wukari': 0})

    def test_export_is_scoped_to_clerk_lgas(self):
        self.submit(self.clerk, self.pu1, 10, 5)
        self.client.force_authenticate(self.clerk)
        r = self.client.get('/api/results/export/')
        self.assertEqual({row['lga'] for row in r.data['polling_units']}, {'Jalingo'})
        first = r.data['polling_units'][0]
        self.assertEqual((first['code'], first['votes'], first['total'], first['reported']),
                         ('34-07-01-001', {'APC': 10, 'PDP': 5}, 15, True))
        self.client.force_authenticate(self.admin)
        r = self.client.get('/api/results/export/', {'ward': self.w_ward.id})
        self.assertEqual([row['polling_unit'] for row in r.data['polling_units']], ['W PU'])

    def test_lga_report_applies_ward_override(self):
        from .models import WardResult
        self.submit(self.clerk, self.pu1, 10, 5)
        WardResult.objects.create(ward=self.ward, party=self.pdp, votes=400)
        self.client.force_authenticate(self.admin)
        r = self.client.get('/api/results/lga_report/', {'lga': self.jalingo.id})
        self.assertEqual(r.data['totals'], {'APC': 10, 'PDP': 400})
        self.assertEqual((r.data['reported'], r.data['polling_units']), (1, 2))
        self.assertTrue(r.data['wards'][0]['override'])
        self.client.force_authenticate(self.clerk)
        self.assertEqual(self.client.get('/api/results/lga_report/', {'lga': self.wukari.id}).status_code, 404)
