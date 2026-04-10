import requests
import time
import os
from urllib.parse import urlparse, parse_qs, unquote

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


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

#L'url du pdf est charger dans un script JS qui ne peux pas etre récupéré
#On va donc simuler une page web (a changer potentiellement plus tard pour un gain de temps / opti)

url = "https://m3c.universita.corsica/s/fr/item/51"


def GetUrl(url):
    '''
    Cette méthode a pour objectif de trouver le lien du fichier pdf afficher sur la page de la M3C
    '''
    #Ouverture de la page web
    options = Options()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    driver.get(url)


    time.sleep(1)
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    div = soup.select_one('iframe')
    try:
        viewer = driver.find_elements(By.CSS_SELECTOR, "octopusviewer-viewer")
        if viewer:
            src = driver.execute_script("""
                const viewer = document.querySelector('octopusviewer-viewer');
                if (!viewer) return null;
                if (viewer.shadowRoot) {
                    const iframe = viewer.shadowRoot.querySelector('iframe');
                    if (iframe) return iframe.getAttribute('src');
                }
                const iframe = viewer.querySelector('iframe');
                return iframe ? iframe.getAttribute('src') : null;
            """)
            if src:
                print("[GetUrl] - URL iframe trouvé :", src)
                return src
            else:
                print("[GetUrl] - URL iframe non trouvé")
    except Exception as e :
        return f"Erreur : {e}"
    finally:
        driver.quit()
        print("[GetUrl] - Driver fermer")
    

def DownloadPdf(src):
    '''
    Cette méthode a pour objectif de télécharger le fichier pdf de la source donnée
    dans un premier temps on nettoie l'url de GetUrl en garder le file= puis en le décodant
    ensuite on le télécharge
    https://stackoverflow.com/questions/16566069/url-decode-utf-8-in-python
    https://stackoverflow.com/questions/34503412/download-and-save-pdf-file-with-python-requests-module

    A terme, utiliser ContexteHelper pour avoir le contexte du pdf
    nom, date, langue pour avoir un titre plus pertinant
    '''
    print("[DownloadPdf] - Nettoyage en cours de l'url")
    SrcParse = src.split("file=")[1]
    SrcClean = unquote(SrcParse)
    print(f"[DownloadPdf] - Url nettoyer : {SrcClean}")

    PdfName = 'M3C-'+SrcClean.split("/")[-1]
    print(f"[DownloadPdf] - pdf : {PdfName}")    
    

    print(f"[DownloadPdf] - Requete envoyé")    
    r = requests.get(SrcClean, headers=headers)

    print(f"[DownloadPdf] - Debut du téléchargement")    
    with open(PdfName, 'wb') as f:
        f.write(r.content)
    f.close()

    print("[DownloadPdf] - PDF téléchargé : {PdfName}.pdf")


def PdfStarter(url):
    print('[PdfStarter] --> GetUrl ')
    src = GetUrl(url)
    print('[PdfStarter] --> GetUrl --> DownloadPdf ')
    DownloadPdf(src)


PdfStarter(url)