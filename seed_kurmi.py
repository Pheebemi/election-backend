import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from election.models import LocalGovernmentArea, Ward, PollingUnit

lga = LocalGovernmentArea.objects.get(name='KURMI')

data = {
    'ABONG': [
        'ABONG I, PRIMARY SCHOOL',
        'ABONG II, ABONG G.D.S.S.',
        'ABONYERE, ABONYERE PRIMARY SCHOOL',
        'AKUMBO, AKUMBO VILLAGE',
        'CHON, CHON VILLAGE',
        'GIDAN MAKERI PRI. SCH.',
        'GIDAN ISA, GIDAN ISA VILLAGE HALL',
        'MBISSA, MBISSA VILLAGE',
        'YABORO, YABORO VILLAGE',
    ],
    'AKWENTO/BOKO': [
        'AFFO PRI. SCH.',
        'AFOROBE PRI. SCH.',
        'AKUWO PRI. SCH.',
        'AKWANWE CENTRAL PRIMARY SCHOOL',
        'AKWABE, AKWABE PRIMARY SCHOOL',
        'AKOFORO, AKOFORO PRIMARY SCHOOL',
        'AKONKO, AKONKO PRIMARY SCHOOL',
        'BATU AMANDA, B/AMANDA HALL',
        'BATU KAMINO, B/KAMINO HALL',
        'BURU, BURU PRIMARY SCHOOL',
        'GIDAN ARDO-UMARU PRI. SCH.',
        'GIDAN MBATE PRI. SCH.',
        'KAN-IYAKA, KAN-IYAKA PRIMARY SCHOOL',
        'BURU II, BURU PRIMARY SCHOOL',
        'NDOMBO TOLORI, NDOMBO TOLORI PRIMARY SCHOOL',
        'NYAKWE PRI. SCH.',
        'ZABE, ZABE PRIMARY SCHOOL',
        'ZOKWE, ZOKWE PRIMARY SCHOOL',
    ],
    'ASHUKU/ENEME': [
        'ADOBE, ADOBE TOWN HALL',
        'AMBWE/MBISU, AMBWE MBISU TOWN HALL',
        'ASHUKU I, ASHIKU TOWN HALL',
        'APIKONI PRI. SCH.',
        'GIDAN MAIGURU PRI. SCH.',
        'GUNDUMA PRI. SCH.',
        'KARA-RUWA PRI. SCH.',
        'NAMA-BABA PRI. SCH.',
        'NAMA BABA II/ABONBIYA, ABONBIYA VILLAGE',
        'NAMA-GANGARE PRI. SCH.',
    ],
    'BAISSA': [
        'BAISSA CENTRAL, CENTRAL PRIMARY SCHOOL',
        'BAISSA EAST, BAISSA TOWN HALL',
        'BAISSA NORTH, BAISSA NORTH PRIMARY SCHOOL',
        'AREA COURT BAISSA VILLAGE HEAD I',
        'BAISSA MARKET BAISSA V. HEAD II',
        'NULGE OFFICE BIBLE COLLEGE',
        'MAIN MOTOR PARK DISTRICT HEAD I',
        'GIDAN MALLAM PRI. SCH.',
        'KPAWULA PRI. SCH.',
        'YALKUM PRI. SCH.',
    ],
    'BENTE/GALEA': [
        'BADA KOSHI PRI. SCH.',
        'BENTE/GALEA I, BENTE PRIMARY SCHOOL',
        'GALEA PRI. SCH.',
        'BENTE-SAMA, BAKIN KASUWA',
        'FALI PRI. SCH.',
        'SARKIN BOKA PRI. SCH.',
        'SHUWAKA PRI. SCH.',
        'SUNKURU PRI. SCH.',
    ],
    'BISSAULA': [
        'AKPO, AKPO PRIMARY SCHOOL',
        'BISSAULA PRI. SCH. I',
        'BISSAULA II, OPP. POLICE STATION',
        'GATARI I, GATARI PRIMARY SCHOOL',
        'GATARI II, BAKIN KASUWA',
        'MAISAMARI PRI. SCH.',
        'SUNKURU/AGABI, BAKIN KASUWA',
    ],
    'DIDAN': [
        'DANBEKI MARKET',
        'DANBEKI II, PRIMARY SCHOOL',
        'RECREATION CENTRE DIDAN I',
        'DIDAN MARKET SQUARE DIDAN II',
        'DINDAN III, DIDAN PRIMARY SCHOOL',
        'GIDAN ALI PRI. SCH.',
        'G/MAILAMBA PRI. SCH.',
        'GIDAN SHAJU PRI. SCH.',
        'GIDAN TUKURA GDSS',
        'GIDAN TUKURA II',
        'GIDAN WAYA PRI. SCH.',
        'GIDAN YAMUSA PRI. SCH.',
    ],
    'NDAFORO/GEANDA': [
        'AKUTUKWE PRI. SCH.',
        'GAGARA PRI. SCH.',
        'GWANDA PRI. SCH.',
        'TUDUN HASKE PRI. SCH.',
        'KOFAI NDAFORO PRI. SCH.',
        'NDAFORO I, TOWN HALL',
        'MARKET SQUARE NDAFORO II',
        'NDAFORO PRI. SCH. III',
        'MARKET SQUARE NDAFORO IV',
        'NDAFORO DUTSE PRI. SCH.',
        'TAFARE PRI. SCH.',
        'TSOKUWA PRI. SCH.',
    ],
    'NJUWANDE': [
        'AKIYA PRI. SCH.',
        'AMBO, AMBO PRIMARY SCHOOL',
        'AMBURU, AMBURU PRIMARY SCHOOL',
        'ASHA I, BAKIN KASUWA',
        'ASHA II, ASHA PRIMARY SCHOOL',
        'ASHA PRI. SCH. III',
        'GIDAN YELWA PRI. SCH.',
        'ATTA, ATTA PRIMARY SCHOOL',
        'CHANDAM, BAKIN KASUWA',
        'MAIHULA PRI. SCH.',
    ],
    'NYIDO/TOSSO': [
        'CHIBONG PRI. SCH.',
        'DANBEKI PRI. SCH.',
        'KUFAI PRI. SCH.',
        'CLINIC PREMISES KUFAI SOUTH',
        'NAKA GBARA, KASUWA',
        'NYIDO PRI. SCH. I',
        'NYIDO PRI. SCH. II',
        'MUBI TOSSO, KASUWA',
        'TOSSO PRI. SCH.',
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

print(f'\nDone. {total_created} polling units created for KURMI.')
