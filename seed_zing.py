import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from election.models import LocalGovernmentArea, Ward, PollingUnit

lga = LocalGovernmentArea.objects.get(name='ZING')

data = {
    'BITAKO': [
        'BITAKO IBRAHIM PRIMARY SCHOOL',
        'BITAKO YALI PRIMARY SCHOOL I',
        'BITAKO YALI PRIMARY SCHOOL II',
        'PRIMARY SCHOOL DANSA',
        'JABANSI PRIMARY SCHOOL',
        'MAZARA PRIMARY SCHOOL I',
        'MAZARA PRIMARY SCHOOL II',
        'PRIMARY SCHOOL SABON LAYI JEN',
        'PRIMARY SCHOOL SULE NAYA',
    ],
    'BUBONG': [
        'BOMEH, BOMEH',
        'BUZZA PRIMARY SCHOOL',
        'LAPPO, KWANTI LAPPO',
        'LASARI, LASARI',
        'MAMPALI PRIMARY SCHOOL',
        'NAZIPO, NAZIPO',
        'NBOSUNG PRIMARY SCHOOL',
        'YONKO PRIMARY SCHOOL',
        'ZIPPO PRIMARY SCHOOL',
    ],
    'DINDING': [
        'DANGONG PRIMARY SCHOOL',
        'DEBA YALI, DEBA YALI',
        'DINDING PRIMARY SCHOOL',
        'KOSSA PRIMARY SCHOOL',
        'KUGONG PRIMARY SCHOOL',
        'MANG, MANG',
        'TOLOGWE, KWANTI TOLOGWE',
        'YUKWA PRIMARY SCHOOL',
    ],
    'LAMMA': [
        'BANSI PRIMARY SCHOOL',
        'BUNU BARIKI, BUNU BARIKI',
        'BUNU MASAPO, BUNU MASAPO',
        'DANDI DISPENSARY',
        'DANDI PRIMARY SCHOOL',
        'DONG, KWANTI DONG',
        'GWOLE, GWOLE',
        'KOYU PRIMARY SCHOOL',
        'KWANTI DANZE, KWANTI DANZE',
        'LAMMA PRIMARY SCHOOL I',
        'LAMMA PRIMARY SCHOOL II',
        'MUSA TIKA, MUSA TIKA',
        'NATSIRDE PRIMARY SCHOOL',
    ],
    'MONKIN A': [
        'G.D.S.S. MONKIN',
        'LAMBONG PRIMARY SCHOOL',
        'MONKIN PRIMARY SCHOOL',
        'NEW DEV. AREA OFFICE',
        'NYELLE PRIMARY SCHOOL',
        'OLD DEV. AREA OFFICE',
        'TAVINGWA PRIMARY SCHOOL',
        'VIEWING CENTRE',
    ],
    'MONKIN B': [
        'DAFFE DUTSE, DAFFE DUTSE',
        'IDIRISU DAFFE, IDIRISU DAFFE',
        'JAN KWANI PRIMARY SCHOOL',
        'KOSENSI, KOSENSI PRIMARY SCHOOL',
        'MAPOKO, MAPOKO',
        'NDAKWANTI, NDAKWANTI',
        'NANA AHLI, NANA AHLI',
        'SAGWE, SAGWE PRIMARY SCHOOL',
        'TAVIRI, TAVIRI PRIMARY SCHOOL',
        'UMARU, UMARU DOGWE',
        'VOLASHANKI, VOLASHANKI',
        'YOHANA, YOHANA DOGWE',
        'ZUM, ZUM PRIMARY SCHOOL',
    ],
    'YAKOKO': [
        'BENDI, BENDI',
        'PRIMARY SCHOOL BENBONG',
        'BISOMPORONG, BISOMPORONG PRIMARY SCHOOL',
        'BODUGA, BODUGA PRIMARY SCHOOL',
        'DANG BE, DANG BE PRIMARY SCHOOL',
        'PRIMARY SCHOOL DELLA ADAMU',
        'KOZANG, KOZANG PRIMARY SCHOOL',
        'KWENZANG, KWENZANG PRIMARY SCHOOL',
        'LAKWANTI, LAKWANTI PRIMARY SCHOOL',
        'PRIMARY SCHOOL NYAVO',
        'NYELI, NYELI PRIMARY SCHOOL',
        'SAMARI ZANG, SAMARI ZANG',
        'TABURAZEH, TABURAZEH PRIMARY SCHOOL',
        'PRIMARY SCHOOL TOGOPI',
        'TOLO YABI, TOLO YABI',
        'PRIMARY SCHOOL WAKILI TONKA',
        'YAKOKO I, YAKOKO PRIMARY SCHOOL I',
        'YAKOKO II, YAKOKO PRIMARY SCHOOL II',
    ],
    'ZING A I': [
        'DISTRICT OFFICE I',
        'DISTRICT OFFICE II',
        'IBRAHIM SAMBO I',
        'IBRAHIM SAMBO II',
        'TADOVAH I, TADOVAH PRIMARY SCHOOL I',
        'TADOVAH II, TADOVAH PRIMARY SCHOOL II',
        'TADOVAH III, TADOVAH PRIMARY SCHOOL III',
        'TADOVAH IV, TADOVAH PRIMARY SCHOOL IV',
        'TUNA PO, TUNA PO PRIMARY SCHOOL',
        'TUDUN WADA, TUDUN WADA OPEN SPACE',
    ],
    'ZING A II': [
        'KAGONG, KAGONG PRIMARY SCHOOL',
        'KAKULU I, KAKULU PRIMARY SCHOOL I',
        'KAKULU II, KAKULU PRIMARY SCHOOL II',
        'KAKULU III, KAKULU PRIMARY SCHOOL III',
        'OLD V.T.C., OLD V.T.C.',
    ],
    'ZING B': [
        'GAM PO BONG, GAMPOBONG PRIMARY SCHOOL',
        'JAGAMBO, JAGAMBO PRIMARY SCHOOL',
        'KWANA DISPENSARY, KWANA DISPENSARY',
        'KOKO BUDANG PRIMARY SCHOOL',
        'TAGALANG, TAGALANG PRIMARY SCHOOL',
        'TSOHON GARI, TSOHON GARI PRIMARY SCHOOL',
        'PRIMARY SCHOOL ZANDI GIDA',
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

print(f'\nDone. {total_created} polling units created for ZING.')
