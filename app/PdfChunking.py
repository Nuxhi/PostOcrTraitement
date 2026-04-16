from pypdf import PdfReader
import os 

'''
Extracting the text of a page requires parsing its whole content stream.
This can require quite a lot of memory - we have seen 10 GB RAM being required for an uncompressed content stream of about 300 MB 
(which should not occur very often).

To limit the size of the content streams to process (and avoid OOM errors in your application),
consider checking len(page.get_contents().get_data()) beforehand.
'''

def Path():
    print(os.getcwd())
    os.chdir("pdf")


def NbrPage(pdfname):
    '''
    Affiche le nombre de page du pdf
    Surtout utile pour showText
    '''
    reader = PdfReader(pdfname+'.pdf')
    return len(reader.pages)


def ShowText(pdfname, pageVoulu):
    '''
    permet d'afficher le texte de la page selectionné.    
    '''
    #Path()
    reader = PdfReader(pdfname+'.pdf')
    if pageVoulu > NbrPage(pdfname):
        return "La page selectionnée n'est pas disponile ()"
    page = reader.pages[pageVoulu]
    text = page.extract_text()
    print(text)
    return text
