import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from election.models import LocalGovernmentArea, Ward, PollingUnit

lga = LocalGovernmentArea.objects.get(name='TAKUM')

data = {
    'BETE': [
        'BETE MARKET',
        'BETE PRI. SCH.',
        'SECONDARY SCH. BETE',
        'GAMGA, GAMGA PRIMARY SCHOOL',
        'KOFAR. S/BIBI, PRIMARY SCHOOL',
        'LUKPO, LUKPO PRIMARY SCHOOL',
        'MPANG MARKET',
        'SABON GIDA BETE, S/G. BETE PRIMARY SCHOOL',
        'TAMPA MARKET',
        'WOROBO MARKET',
    ],
    'CHANCHANJI': [
        'MINI MARKET DAKAR',
        'DAMEVER CLINIC',
        'DOGON GAWA, DOGON GAWA PRIMARY SCHOOL',
        'DOSHIMA TV AV MARKET',
        'IGBUN PRIMARY SCHOOL',
        'INGOOV PLAYGROUND',
        'ADJACENT POLICE STATION CHANCHANJI',
        'MBALAM SHINKU PRI. SCH.',
        'MBAPHINE MARKET',
        'MBATATO MBAYEKEIOR PRI. SCH.',
        'MBAYOUM TORTSEE PRI. SCH.',
        'MBAYOUM MICHARI',
        'NEW GBOKO MARKET',
        'K/AHMADU, K/AHMADU PRI. SCHOOL',
        'TSAREV TOWN HALL',
        'TSE AUDU PLAY GROUND',
        'TSEPEEKI FOOTBALL GROUND',
        'TYOLUMOUN PRI. SCH.',
        'YELWA PRI. SCH.',
        'YELWA TOWN HALL',
    ],
    'DUTSE': [
        'BASANG PRI. SCH.',
        'DINYINA PRI. SCH.',
        'FADAMA, FADAMA OPEN SPACE',
        'FANWE PRI. SCH.',
        'KOFAR GALADIMA, KOFAR GALADIMA',
        'TOWN HALL OPPOSITE KOFAR SARKI UKAM',
        'TOWN HALL, ADJACENT KOFAR UKWE',
        'PLAY GROUND OPPOSITE KOFAR RICHUMAN I',
        'PLAY GROUND OPPOSITE KOFAR RICHUMAM II',
        'PLAY GROUND OPPOSITE KOFAR SHITEN',
        'MBARIKAM MARKET',
        'MBARIKAM PLAY GROUND',
        'GOVT. SEC. SCH., MBIYA',
        'GOVT. SEC. SCH., MUJI I',
        'MUJI PRI. SCH. II',
        'TAMPA PRIMARY SCHOOL I',
        'TAMPA PRI. SCH. II',
        'TANYI PRIMARY SCHOOL',
        'TUDUN PRI. SCH.',
        'WOMEN EDUCATION CENTRE',
    ],
    'FETE': [
        'GALUMJE, GALUMJE PRIMARY SCHOOL',
        'FETE, FETE PRIMARY SCHOOL',
        'KAPYA PLAY GROUND',
        'KAPYA TOWN HALL',
        'KUFI PLAY GROUND',
        'LUFU I, LUFU PRIMARY SCHOOL',
        'LUFU II, LUFU PRIMARY SCHOOL',
        'SUFA, SUFA PRIMARY SCHOOL',
        'TAMPA PLAY GROUND',
        'YERI PLAY GROUND',
    ],
    'GAHWETON': [
        'ALHERI PRIMARY SCHOOL',
        'HENRY PORTER, HENRY PORTER PRIMARY SCHOOL',
        'TOWN HALL OPP K/S JUKUN TSOHO I',
        'PUBLIC SQUARE ADJACENT K/S JUKUN I SABO',
        'TOWN HALL ADJACENT K/S JUKU SABO II',
        'LUFU, RIMI PRIMARY SCHOOL',
        'MBAKPA PLAY GROUND',
    ],
    'BIKASHIBILA': [
        'ANGWAN MADAKI PLAYGROUND',
        'KASHIMLA CLINIC, ANGWAN MAHARBA',
        'KASHIMBILA OLD MARKET, BAKIN KASUWA',
        'GAMAVOU MARKET',
        'JATAU PRI. SCH.',
        'BIRAMA MARKET KOFAR BIRAMA',
        'MALUMSHE PLAYGROUND',
        'MALUMSHE MARKET, TUNWARI',
        'MATAZUN FOOTBALL GROUND',
        'MGBE, MGBE PRIMARY SCHOOL',
    ],
    'MANYA': [
        'GANGUM FOOTBALL FIELD',
        'MANYA MARKET SQUARE',
        'KOFAR SARKI II, KOFAR SARKI II',
        'MANYA TOWN HALL',
        'SHINKAFA MARKET, SHINKAFA',
        'TATI KUMBO, T/KUMBO PRIMARY SCHOOL',
    ],
    'ROGO': [
        'ABUJA OLD GARAGE TAKUM',
        'DAKATSALE FOOTBALL FIELD',
        'DAMA FOOTBALL FIELD',
        'MAMI MARKET BARRACK, HAWAN SHANU',
        'IORNUMBE FOOTBALL FIELD',
        'KAROFI PLAYGROUND',
        'FOOTBALL FIELD ADJACENT K/BABANNANA',
        'OPPOSITE K/SARKI PLAY GROUND',
        'KOFAR/MAJE FOOTBALL FIELD',
        'ADJACENT PLAY GROUND KOFAR/LIMAN',
        'WADATA FOOTBALL FIELD',
    ],
    'SHIBONG': [
        'BARKI LISSAM MARKET',
        'BARKI LISSAM PLAY GROUND',
        'GATATI, GATATI PRIMARY SCHOOL',
        'MANGA PLAY GROUND',
        'SHIBONG MARKET',
        'LIJI, LIJI PRIMARY SCHOOL',
        'SHIBONG IGBANG TOWN HALL',
    ],
    'TIKARI': [
        'BARIYA PLAY GROUND',
        'JIDU MARKET',
        'ADJACENT KOFAR WAKILI',
        'KUNATAMI MARKET',
        'PATI FOOTBALL GROUND',
        'TANJI HASKE MARKET',
        'TIKARI PLAY GROUND',
        'TIKARI TOWN HALL',
    ],
    'YUKUBEN': [
        'ACHA NYIM PLAYGROUND',
        'ACHA SARKA, ACHA SARKA PRIMARY SCHOOL',
        'LUTU FOOTBALL FIELD',
        'OPPOSITE KOFAR SARKI',
        'MAMU SABO MARKET',
        'NYAYIRIM I, NYAYIRIM PRIMARY SCHOOL',
        'NYAYIRIM II, NYAYIRIM PRIMARY SCHOOL',
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

print(f'\nDone. {total_created} polling units created for TAKUM.')
