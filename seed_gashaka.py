import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from election.models import LocalGovernmentArea, Ward, PollingUnit

lga = LocalGovernmentArea.objects.get(name='GASHAKA')

data = {
    'GALUMJINA': [
        'ABBA DOGO, ABBA DOGO',
        'BALEWA, BALEWA',
        'BODEL, BODEL',
        'GALUMJINA, GALUMJINA',
        'GAMEN, GAMEN',
        'SARKIN RUWA, SARKIN RUWA',
    ],
    'GANGUMI': [
        'AFENGI OPEN SPACE',
        'GANGUMI PRI. SCH.',
        'KOFAI PRI. SCH.',
        'GANTI OPEN SPACE',
        'GANG BONG PRI. SCH. I',
        'GANG BONG PRI. SCH. II',
        'GANGUMI IORMBA OPEN SPACE',
        'GARIN TIV, GARIN TIV',
        'KARE PRI. SCH.',
        'KAME PRI. SCH.',
        'KWAGIR, KWAGIRI PRIMARY SCHOOL',
    ],
    'GARBABI': [
        'BASHIR SHIR PRI. SCH.',
        'BASHIR SHIR GAB PRI. SCH. & KUNA PRIMARY SCH.',
        'DUNA PRI. SCH.',
        'GARBABI PRI. SCH.',
        'MARKET SQUARE',
        'JAURO JALO PRI. SCH.',
        'DISPENSARY, K. BATURE',
        'ANG AJAYI PRI. SCH.',
        'UPPER WAYA, PRIMARY SCHOOL',
    ],
    'GASHAKA': [
        'CHABBAL DALANG',
        'CHABBA HENDU PRI. SCH.',
        'GASHAKA GUMTI NATIONAL PARK CAMP FILLINGA',
        'GASHAKA PRI. SCH. I',
        'GASHAKA PRI. SCH. II',
        'SELBE, SELBE',
    ],
    'GAYAM': [
        'GAYAM I, PRIMARY SCHOOL',
        'GAYAM II, MUDAI',
        'KUNFAN, PRIMARY SCHOOL',
        'SHINBON, SHINBON',
        'SHINAM, SHINAM',
        'PANWAI, PANWAI',
    ],
    'JAMTARI': [
        'ADDA GORO, ADDA GORO',
        'JAMTARI I, PRIMARY SCHOOL',
        'JAMTARI II, NYIBANGO',
        'KARAMTI I, PRIMARY SCHOOL',
        'KARAMTI II, KOTI',
        'KWAITAP, KWAITAP',
        'MAYO JAMTARI, M/JAMTARI',
        'SALAMA, SALAMA',
    ],
    'MAI-IDANU': [
        'BAM I, BAM',
        'BAM II, MAI-IDANU',
        'DAKARE, DAKARE',
        'GINDIN DUTSE PRIMARY SCHOOL',
        'MBAR MATAYA, MBAR MATAYA',
        'MAYO SABERE, MAYO SABERE',
    ],
    'MAYO SELBE': [
        'GOJE I PRIMARY SCHOOL',
        'GOJE II, LIKWAL',
        'MAYO JARANDI, MAYO JARANDI',
        'MAYO SELBE I, M.O.W.',
        'MAYO SELBE II, LARA ASHA',
        'M/SELBE PRIMARY SCHOOL, PRIMARY SCHOOL',
    ],
    "SERTI 'A'": [
        'CENTRAL PRIMARY SCHOOL, CENTRAL PRIMARY SCHOOL',
        'KOFAR FADA I, KOFAR FADA',
        'KOFAR FADA II, KOFAR FADA',
        'KOFAR FADA III, UNG. ISA',
        'L.G. DISPENSARY, L.G. DISPENSARY',
        'MIN. OF AGRIC. I, MIN. OF AGRIC',
        'MIN. OF AGRIC. II, TUDUN WADA',
    ],
    "SERTI 'B'": [
        'ALPHA CLINIC, ALPHA CLINIC',
        'DADIN KOWA I PRIMARY SCHOOL',
        'DADIN KOWA II PRIMARY SCHOOL',
        'MAMMY MARKET I, MAMMY MARKET',
        'MAMMY MARKET II, MAMMY MARKET',
        'SABON GARI, SABON GARI',
        'TOWNSHIP STADIUM, TOWNSHIP STADIUM',
        'VERTERINARY CLINIC, VERTERINARY CLINIC',
    ],
}

total_created = 0

for ward_name, pus in data.items():
    ward = Ward.objects.get(name=ward_name, lga=lga)
    for i, pu_name in enumerate(pus, start=1):
        pu, created = PollingUnit.objects.get_or_create(
            name=pu_name,
            ward=ward,
            defaults={'code': str(i).zfill(3)}
        )
        if created:
            total_created += 1
            print(f'  Created: [{ward_name}] {pu_name}')
        else:
            print(f'  Exists:  [{ward_name}] {pu_name}')

print(f'\nDone. {total_created} polling units created for GASHAKA.')
