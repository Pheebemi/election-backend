import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from election.models import LocalGovernmentArea, Ward, PollingUnit

lga = LocalGovernmentArea.objects.get(name='LAU')

data = {
    'ABBARE I': [
        'AHMADU I / ABBARE PRI. SCH.',
        'AHMADU II, ABBARE PRIMARY SCHOOL',
        'FULANI MARKET, FULANI MARKET',
        'KOFAR HASSAN OPEN SPACE',
        'PALIYA OPEN SPACE',
    ],
    'ABBERE II': [
        'BUJUM KASUWA, BUJUM PRIMARY SCHOOL',
        'BUJUM WAYA OPEN SPACE',
        'G.D.S.S. I, GOVERNMENT DAY SECONDARY SCHOOL',
        'G.D.S.S. II, GOVERNMENT DAY SECONDARY SCHOOL',
        'KWAMIDING PRI. SCH.',
        'SABON GIDA, SABON GIDA PRIMARY SCHOOL',
        'TANA BABBA, TANA BABBA PRIMARY SCHOOL',
        'YITTI, YITTI PRIMARY SCHOOL',
    ],
    'DONADDA': [
        'ARDIDO MAKO, ARDIDO PRIMARY SCHOOL',
        'BUBA UMARU OPEN SPACE',
        'BWEI NYANKWELEY, BWEI PRIMARY SCHOOL',
        'DONADDA PRIMARY SCHOOL',
        'GARIN BORORI OPEN SPACE',
        'HAMMAN BURA OPEN SPACE',
        'JUGGOL, JUGGOL PRIMARY SCHOOL',
        'KATIBU I, KATIBU PRIMARY SCHOOL',
        'KATIBU II, KATIBU PRIMARY SCHOOL',
    ],
    'GARIN DOGO': [
        'DANJUMA GARBA OPEN SPACE',
        'JAURO AZOH OPEN SPACE',
        'JAURO NYAVO OPEN SPACE',
        'LAINDE, LAINDE PRIMARY SCHOOL',
        'LUSHI OPEN SPACE',
        'SARKIN GARIN DOGO I OPEN SPACE',
        'SARKIN G/DOGO II, GARIN DOGO PRIMARY SCHOOL',
        'SARKIN KAUDA OPEN SPACE',
        'SARKIN MINDAH I, MINDAH PRIMARY SCHOOL',
        'SARKIN MINDAH II, MINDAH PRIMARY SCHOOL',
    ],
    'GARIN MAGAJI': [
        'ARDIDO YUSA OPEN SPACE',
        'GARIN MAGAJI, GARIN MAGAJI PRIMARY SCHOOL',
        'JAMBUTU, JAMBUTU PRIMARY SCHOOL',
        'KASUWAN JAKI, L.G. CLINIC',
        'MIJINYAWA OPEN SPACE',
        'YUSA FULANI, YUSA FULANI PRIMARY SCHOOL',
    ],
    'JIMLARI': [
        'ARDIDO MARKET, ARDIDO MARKET',
        'APPAWA LUBBE, LUBBE PRIMARY SCHOOL',
        'APPAWA MARKET, APPAWA MARKET',
        'APPAWA PRIMARY SCHOOL I',
        'APPAWA PRIMARY SCHOOL II',
        'BAYU OPEN SPACE',
        'FULANI NYAKINTI PRI. SCH.',
        'JIMLARI PRIMARY SCHOOL',
        'SABUKARU, SABUKARU PRIMARY SCHOOL',
        'OPEN SPACE SULEIMAN',
        'OPEN SPACE WAKILI',
    ],
    'KUNINI': [
        'KUNINI NORTH PRI. SCHOOL I',
        'BUBA GEDE, DEVT. AREA OFFICE',
        'GARIN SARKI I, G/SARKI PRIMARY SCHOOL',
        'GARIN SARKI II, G/SARKI PRIMARY SCHOOL',
        'JAURO TUKUR KOFAR OPEN SPACE',
        'KUNINI PRIMARY SCHOOL',
        'MAISAJE OPEN SPACE',
        'RUNDE OPEN SPACE',
    ],
    'LAU I': [
        'GWAWI, LAU MOTOR PARK',
        'KOFAR SARKI I, LAU AREA COURT',
        'KOFAR SARKI II, LAU AREA COURT',
        'KIRI GALADIMA, LAU CENTRAL PRIMARY SCHOOL',
        'MUHAMMADU, LAU MATERNITY CLINIC',
        'MUSA HABU I OPEN SPACE',
        'MUSA HABU II OPEN SPACE',
        'KOFAR MAL. ZAKARI OPEN SPACE',
        'SAIDU MUSA OPEN SPACE',
        'UNG. MASHI, L.G. CLINIC',
        'YARO SUGUDA, LAU NURSERY SCHOOL',
    ],
    'LAU II': [
        'BUBA BACHAMA OPEN SPACE',
        'DOUBELI, DOUBELI PRIMARY SCHOOL',
        'GARIN BAKARI, G/BAKARI PRIMARY SCHOOL',
        'JUNGO, KOFAR TABAH OPEN SPACE',
        'KABAWA, KABAWA PRIMARY SCHOOL',
        'RIGI SIYASA PRI. SCH.',
        'SHOMO SARKI I, SHOMO SARKI PRIMARY SCHOOL',
        'SHOMO SARKI II, SHOMO SARKI PRIMARY SCHOOL',
    ],
    'MAYO LOPE': [
        'KOFAR ADAMU OPEN SPACE',
        'BUDON, BUDON PRIMARY SCHOOL',
        'KOFAR BARDE OPEN SPACE',
        'MISHELI, MISHELI PRIMARY SCHOOL',
        'WATAKILA I, WATAKILA MARKET',
        'WATAKILA II/BUDING OPEN SPACE',
        'SAYONTI, SAYONTI PRIMARY SCHOOL',
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

print(f'\nDone. {total_created} polling units created for LAU.')
