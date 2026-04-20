import requests
from bs4 import BeautifulSoup

try:
    from app.headers import headers
except ModuleNotFoundError:
    from headers import headers


REQUEST_HEADERS = headers()


def extract_field(soup_obj, data_type):
    node = soup_obj.select_one(
        f'div.accordion__item[data-type="{data_type}"] span.accordion__content'
    )
    if not node:
        return None
    return " ".join(node.stripped_strings)

def startExtraction(url):

    reponse = requests.get(url, headers=REQUEST_HEADERS, timeout=15)
    reponse.raise_for_status()
    #print(f"Status: {reponse.status_code}")
    soup = BeautifulSoup(reponse.text, "html.parser")


    infos = {
        "titre": extract_field(soup, "dcterms:title")
        or (soup.select_one("h2.page-header__title").get_text(strip=True) if soup.select_one("h2.page-header__title") else None),
        "description": extract_field(soup, "dcterms:description"),
        "date": extract_field(soup, "dcterms:date"),
        "couverture_temporelle": extract_field(soup, "dcterms:temporal"),
        "langue": extract_field(soup, "dcterms:language"),
    }

    return infos


def GetInfo(url, info):
    '''
    Cette methode permet de récupéré des informations depuis l'url fournis
    '''
    print(f"[GetInfo] - Extraction de l'information : {info}")
    infodic = startExtraction(url)

    if info == 'all':
        for cle, valeur in infodic.items():
            print(cle, valeur, '\n')
        return infodic

    if info in infodic:
        print(f"[GetInfo] - Information trouvé : {infodic[info]}")
        return infodic[info]

    print("information non comprise")
    return False