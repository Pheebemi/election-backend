import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from election.models import LocalGovernmentArea, Ward, PollingUnit

lga = LocalGovernmentArea.objects.get(name='YORRO')

data = {
    'BIKASSA I': [
        'DINYA, A MINI MARKET PLACE',
        'GAMPU, LOCAL GOVERNMENT DISPENSARY',
        'KASSA, KASSA PRIMARY SCHOOL',
        'KOKING PRI. SCH.',
        'KUNZANG, KUNZANG PRIMARY SCHOOL',
        'PANTI KAYYA, KAYYA PRIMARY SCHOOL',
    ],
    'BIKASSA II': [
        'BARIKI DANKUM, A MINI MARKET PLACE',
        'BONSHALA PRI. SCH.',
        'DANKUM I, DANKUM PRIMARY SCHOOL',
        'DANKUM PRI. SCH. PANTIS PALACE',
        'DOKIN, DOKIN PRIMARY SCHOOL',
        'GANGORO PRI. SCH.',
        'KUKOPO, A MINI MARKET PLACE',
        'SARKIN FADA OPEN SPACE',
        'YERIMA JAVO PRI. SCH.',
    ],
    'NYAJA I': [
        'GOMBEJO PRI. SCH.',
        'LANKO, LANKO PRIMARY SCHOOL',
        'NYAJA LAPU, NYALADI GORKO PRIMARY SCHOOL',
        'PANTI BURI, PANTI BURI PRIMARY SCHOOL',
        'PANTI NYAJA, A MINI MARKET PLACE',
        'UNKWA, UNKWA PRIMARY SCHOOL',
    ],
    'NYAJA II': [
        'PANTI BUBUTU PRI. SCH.',
        'KAJONG I PRI. SCH.',
        'PANTI KAJONG II, PANTI YESSING PRIMARY SCHOOL',
        'PANTI NTARI, SHONPA PRIMARY SCHOOL',
    ],
    'PANTISAWA I': [
        'DILA I, DILA PRIMARY SCHOOL',
        'PRI. SCH., DILA WAKILI GWAMBA',
        'DI-KUNZANG OPEN SPACE',
        'GDSS P/SAWA, GDSS PANTI SAWA',
        'NYALADI, NYALADI PRIMARY SCHOOL',
        'ALI PRI. SCH.',
        'PANTI LACHEKE, GADDA PRIMARY SCHOOL',
        'PANTISAWA I, PANTISAWA PRIMARY SCHOOL',
        'PRI. SCH., PANTISAWA II, UNGUWAN FADA',
        'PANTI SORENG, SORENG PRIMARY SCHOOL',
    ],
    'PANTISAWA II': [
        'VOROBI PRI. SCH.',
        'LAPU I, LAPU PRIMARY SCHOOL',
        'PRI. SCH., LAPU II, YALI SENSO',
        'DASSO PRI. SCH.',
        'WAKILI PUGON, WAKILI PUGON PRIMARY SCHOOL',
    ],
    'PUPULE I': [
        'DANZANG, DANZANG PRIMARY SCHOOL',
        'MANZALANG PRI. SCH.',
        'OLD KWAJJI I, OLD KWAJJI PRIMARY SCHOOL',
        'OLD KWAJJI II, KASUWAN TAYA KWAJJI',
        'PABENZANG, A MINI MARKET PLACE',
        'PUPULE, PUPULE PRIMARY SCHOOL',
        "PUPULE'S MARKET OPEN SPACE, UNGUWAN FADA",
    ],
    'PUPULE II': [
        'BOLI MIKA, BOLI MIKA PRIMARY SCHOOL',
        "DAMPANG OPEN SPACE NEAR JAURO'S PALACE",
        'LAYANG WEREBANG, LAYANG PRIMARY SCHOOL',
        'MIKA MARARABA I, A MINI MARKET',
        'MIKA MARARABA II, DAN YALA OPEN SPACE',
        'NARAPO BORO, MIKA PRIMARY SCHOOL',
        'SHOMMAN, LOCAL GOVERNMENT DISPENSARY',
    ],
    'PUPULE III': [
        'BOLI SABO, BOLI SABO PRIMARY SCHOOL',
        'DANDIKULU, DANDIKULU PRIMARY SCHOOL',
        'DOGAN ALKALI PRI. SCH.',
        'GOPA SANYORI, DOGOPI PRIMARY SCHOOL',
        'JIKA I, JIKA PRIMARY SCHOOL',
        'JIKA II, YAZOKU OPEN SPACE',
        'MABANG, MABANG PRIMARY SCHOOL',
        'MANANG, MANANG PRIMARY SCHOOL',
        'NADAVIBA, A MINI MARKET',
    ],
    'SUMBU I': [
        'U.B.E PRI. SCH. JAURO A. FULANI',
        'SANTUWA PRI. SCH. JAURO FARUKU',
        'LANKAVIRI DISPENSARY, LOCAL GOVERNMENT DISPENSARY',
        'LANKAVIRI GDSS I',
        'LANKAVIRI GDSS II',
        'LANKAVIRI PRIMARY I, LANKAVIRI PRIMARY SCHOOL',
        'UNGUWAN HAUSA OPEN SPACE',
        'PANTI BASHENG PRI. SCH.',
        'PANTINAPU, PANTI NAPU PRIMARY SCHOOL',
    ],
    'SUMBU II': [
        'MALAM AUDU PRI. SCH.',
        'GONGON PRI. SCH.',
        'PANTI KIR, PANTI KIR PRIMARY SCHOOL',
        'TENDANG PRI. SCH.',
        'ZAMPA, ZAMPA PRIMARY SCHOOL',
        'ZAVO RANTI, MINI MARKET',
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

print(f'\nDone. {total_created} polling units created for YORRO.')
