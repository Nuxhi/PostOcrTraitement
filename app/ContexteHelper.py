import requests
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "document",
    "sec-ch-ua": "\"Google Chrome\";v=\"135\", \"Chromium\";v=\"135\", \"Not.A/Brand\";v=\"24\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "Cache-Control": "max-age=0"
}


def extract_field(soup_obj, data_type):

    node = soup_obj.select_one(
        f'div.accordion__item[data-type="{data_type}"] span.accordion__content'
    )
    if not node:
        return None
    return " ".join(node.stripped_strings)

def startExtraction(url):

    reponse = requests.get(url, headers=headers, timeout=15)
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