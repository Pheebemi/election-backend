import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from election.models import LocalGovernmentArea, Ward, PollingUnit

lga = LocalGovernmentArea.objects.get(name='USSA')

data = {
    'BIKA': [
        'FOOTBALL FIELD NEAR VENSTRA COLLEGE, LUPWE',
        'G D.S.S BIKA BABA',
        'KWENSAIC PRI. SCH.',
        'BIKA BABA PRI. SCH.',
    ],
    'FIKYU': [
        'L.G DISPENSARY FIKYU',
        'FIKYU BAKIN KASUWA I',
        'FIKYU BAKIN KASUWA II',
        'COMPREHENSIVE SEC. SCH. FIKYU',
        'G.D.S.S NYIKUN',
    ],
    'JENUWA': [
        'RIKYA COMMUNITY SEC. SCH.',
        'NYICWU PRI. SCHOOL',
        'NYIFIYE PRI. SCH. I',
        'GDSS NYIFIYE II',
        'RIKWENYAKWEN PRI. SCH.',
        'RIKWENMBOI PRI. SCH.',
        'RUWU PRI. SCH.',
        'JENUWA GIDA PRI. SCH.',
        'UKOK PRI. SCH.',
    ],
    'KPAMBO': [
        'GDJSS GALUMJE',
        'KPAMBO PRI. SCH.',
        'RIYANG PRI. SCH.',
        'ROUNABOUT PRI. SCH.',
        'UKWA PRI. SCH.',
        'YIWARE PRI. SCH.',
        'YIROM PRI. SCH.',
        'KABRISI PRI. SCH.',
    ],
    'KPAMBO PURI': [
        'KPAMBO PURI I, KPAMBO PURI PRIMARY SCHOOL',
        'KPAMBO PURI II, KPAMBO PURI PRIMARY SCHOOL',
        'YASHE PRI. SCH.',
        'KWENTIKI PRIMARY SCHOOL',
        'LISSAM SAMBO I, LISSAM SAMBO PRIMARY SCHOOL',
        'LISSAM JATAU, LISSAM JATAU PRIMARY SCHOOL',
        'PANTSO PRI. SCH.',
    ],
    'KWAMBAI': [
        'JENUWA KOGI, J/KOGI PRIMARY SCHOOL',
        'TOWN HALL KOFAR IGBAN KISABA',
        'KWAMBAI PRI. SCH.',
        'COMPREHENSIVE HEALTH CENTRE',
        'KOFAR SARIKI PRI. SCH.',
        'BAKIN KASUWA KOFAR USMAN',
        'KWENDO PRI. SCH.',
        'LIMPA PRI. SCH.',
        'NZUNYI PRI. SCH.',
        'RUBUR KAPYA PRI. SCH.',
        'WAEYI PRI. SCH.',
    ],
    'KWESATI': [
        'ANDEUSSA I, ANDEUSSA PRIMARY SCHOOL',
        'SISEAN PRI. SCH.',
        'AYIYI PRI. SCH.',
        'KUSANSANG, KUSANSANG PRIMARY SCHOOL',
        'KWESATI I, KWESATI PRIMARY SCHOOL',
        'TUTUWA, TUTUWA PRIMARY SCHOOL',
    ],
    'LISSAM I': [
        'KADUNA LISSAM PRI. SCH. I',
        'KADUNA LISSAM PRI. SCH. II',
        'POST OFFICE KOFAR KWE AGO',
        'KOSTINE PRIMARY SCHOOL, LISSAM CENTRAL PRIMARY SCHOOL',
        'KUTUPWEN I, KUTUPWEN PRIMARY SCHOOL',
        'KUTUPWEN II PRI. SCH.',
        'YAMUSA, YAMUSA PRIMARY SCHOOL',
    ],
    'LISSAM II': [
        'KAKOM PRI. SCH.',
        'LISSAM FOOTBALL FIELD',
        'KUNKUFXANG PRI. SCH. I',
        'WOMEN CENTRE KUNKUFXANG II',
        'LISSAM MATERNITY CLINIC',
        'TAMIYA/LUPWE, LUPWE PRIMARY SCHOOL',
    ],
    'LUMBU': [
        'KPAKYA, KPAKYA PRIMARY SCHOOL',
        'KPAKYA, KPAKYA MARKET',
        'LUMBU YAUSSA, LUMBU YAUSSA PRIMARY SCHOOL',
        'RIKWENRIKA, RIKWENRIKA PRIMARY SCHOOL',
        'WEAKWAM PRI. SCH.',
    ],
    'RUFU': [
        'G.D.S.S. RUFU, G.D.S.S. RUFU',
        'BAKIN KASUWA KOFAR MUSA AKAMA',
        'RUFU BAKIN KASUWA I, BAKIN KASUWA',
        'RUFU B/K KUTUFA, PRIMARY SCHOOL KUTUFA',
        'RUFU PRIMARY SCHOOL, RUFU PRIMARY SCHOOL',
        'YITSANG, YITSANG PRIMARY SCHOOL',
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

print(f'\nDone. {total_created} polling units created for USSA.')
