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
