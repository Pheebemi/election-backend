import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from election.models import LocalGovernmentArea, Ward, PollingUnit

lga = LocalGovernmentArea.objects.get(name='IBI')

data = {
    'DAMPAR I': [
        'GDSS DAM PAR',
        'ISHAKU PRI. SCHOOL',
        'HAMMAN OPEN SPACE',
        'KORIJO, UN GUWAN KORIJO',
        'KOFAN TSOHO OPEN SPACE',
        'WAZIRI, KOFAN WAZIRI',
    ],
    'DAMPAR II': [
        'DALI/MAVO, MAVO',
        'NOMADIC PRI. SCHOOL',
        'KURMI I, G/DUDU',
        'KURMI SAURI PRI.SCHOOL',
        'MALA, MALA PRIMARY SCHOOL',
        'RUWAN DAN BAKI, RUWAN DAN BAKI',
    ],
    'DAMPAR III': [
        'ANG.KWALA PRI. SCHOOL',
        'DAN GIWA II, KOFAN MAIANGUWA',
        'DANWASE, DANWASE',
        'KOGIN WASE, KOGIN WASE PRIMARY SCHOOL',
        'KOTSO BABBA, KOTSO BABBA',
        'PRIMARY HEALTH CARE MAJE BIYU',
        'TABGA, TABGA PRIMARY SCHOOL',
    ],
    'IBI NWONYO I': [
        'KOFAN SARKINMAKERA OPEN SPACE',
        'KOFAN ALH.MAIDA OPEN SPACE',
        'KOFAR BALA MAYE OPEN SPACE',
        'BABA BUREMA I, TOWN DISPENSARY',
        'KOFAR SARKIN HANYA OPEN SPACE',
        'KOFAR MAI ANGUWA OPEN SPACE',
        'KOFAR SARKIN IBI OPEN SPACE',
        'KOFAR MAKERA OPEN SPACE',
        'MADAKIN PAWA OPEN SPACE',
        'MADAKIN TARU OPEN SPACE',
        'MUSA MANAJA DAMPAR, KOFAR MUSA MANAJA',
        'KOFAR TAFIDA OPEN SPACE',
        'KOFAR WAZIRI BANU OPEN SPACE',
    ],
    'IBI NWONYO II': [
        'ALH. TAMA I OPEN SPACE',
        'ALH. TAMA II OPEN SPACE',
        'MINISTRY OF AGRIC',
        'GAZOR, GAZOR PRIMARY SCHOOL',
        'POST OFFICE IBI',
        'IBUA, IBUA PRIMARY SCHOOL',
        'JIGAWAN GYADA OPEN SPACE',
        'SABON PEGI II PRI. SCHOOL',
        'ZENNA PRI. SCHOOL',
        'MOTI, MOTI PRIMARY SCHOOL',
        'MOHAMMADU FARI OPEN SPACE',
        'TUDUN WADA, TUDUN WADA PRIMARY SCHOOL',
        'ORTUMA, ZANGON KAYA',
    ],
    'IBI RIMI UKU I': [
        'COURAGE HOSPITAL IBI',
        'BOREHOLE II SABON PEGI',
        'ABDU KANO KANJE OPEN SPACE',
        'ALI SARKIN PAWA I, KOFAR BABA DAN YARO',
        'ALI SARKIN PAWA OPEN SPACE',
        'DAN LAMI NA IBI OPEN SPACE',
        'ISLAMIYA, ISLAMIYA PRIMARY SCHOOL',
        'KAUYEN ISA, KOFAR MAIANGUWA',
        'SARKIN ASKA OPEN SPACE',
        'SANKIRA OPEN SPACE',
        'SARKIN TASHA OPEN SPACE',
    ],
    'IBI RIMI UKU II': [
        'BAKYU, BAKYU PRIMARY SCHOOL',
        'DAN KAMATA OPEN SPACE',
        'GINDIN WAYA, GINDIN WAYA PRIMARY SCHOOL',
        'KAUYEN GWAGH NGU OPEN SPACE',
    ],
    'SARKIN KUDU I': [
        'GALADIMA OPEN SPACE',
        'KOFAR MADAKI OPEN SPACE',
        'ANGUWAN MASU OPEN SPACE',
        'KOFAR SARKIN BAKA OPEN SPACE',
        'GIDAN YAMEER OPEN SPACE',
    ],
    'SARKIN KUDU II': [
        'DORUWAN KWANVEN',
        'SABON LAYI OPEN SPACE',
        'DOUBLE CORNER OPEN SPACE',
        'RAFIN DAMISA OPEN SPACE',
        'KWAMAR, KWAMAR PRIMARY SCHOOL',
    ],
    'SARKIN KUDU III': [
        'BAKAANDOSHIMA OPEN SPACE',
        'DOOSHIMA, DOOSHIMA PRIMARY SCHOOL',
        'GISHIRIN HASSAN, GISHIRIN HASSAN DISPENSARY',
        'GURBIN DUTSE OPEN SPACE',
        'TOR ADI OPEN SPACE',
        'TOR KANGE OPEN SPACE',
        'K. GARBA WANZAMI OPEN SPACE',
        'UZER, UZER PRIMARY SCHOOL',
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

print(f'\nDone. {total_created} polling units created for IBI.')
