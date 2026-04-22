'''
POST OCR to correction with LLM
APP VERSION : 0.1
STATE : ALPHA
'''

'''
Item : https://m3c.universita.corsica/s/fr/item/15
'''

import app.CheckModel as CheckModel
import app.ContexteHelper as ContexteHelper
import app.SystemPrompt as SystemPrompt
import app.PdfDownloader as PdfDownloader
import app.PdfChunking as PdfChunking
import app.MetricsCerWer as MetricsCerWer
import app.Llm as Llm

import os
import re
from datetime import datetime



modelListe = ['mistral', 'llama3:8b', 'qwen3-vl:8b']
model = modelListe[1] #Choix du modèle
api = False #Utile pour le local uniquement, à changer plus tard pour une question d'optimisation

CheckModel.checkModel(model)
MetricsCerWer.configureModel(model)
    
def getLabelScore(txt):
  details = MetricsCerWer.scoreDetails(txt)
  print("algo_score:", round(details["algo_score"], 3))
  print("llm_label:", details["llm_label"])
  print("final_label_value:", details["final_label_value"])
  return details["final_label_value"]
   

def write(txt, i, opignion):
  '''
  Cette méthode permet d'écrire le texte corrigé dans un fichier de sortie.
  Le nom du fichier est généré à partir du nom du modèle utilisé et de la date de traitement.
  '''
  global model, api
  ################# IA ############################
  Suffilename = datetime.now().strftime("pdf-%d-%m-%H")
  #safe_model = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", str(model)).strip(" .")
  print(f"model : {model} - api : {api}")
  if api:
      safe_model = "MistralAPI"
  else:
    safe_model = model.split(":")[0] 
  
  if not safe_model:
      safe_model = "model"
  
  filename = f"{safe_model}{Suffilename}"
  
  project_root = os.path.dirname(os.path.abspath(__file__))
  output_dir = os.path.join(project_root, "output")
  os.makedirs(output_dir, exist_ok=True)

  output_path = os.path.join(output_dir, filename + '.txt')
  #### Plus d'IA  

  #Ne bloque jamais l'ecriture du fichier si le rescoring echoue.
  
  try:
    nouvelleMetrics = getLabelScore(txt)
    print(f"Nouvelle metrics : {nouvelleMetrics}")
  except Exception as exc:
    print(f"[write] rescoring ignore: {exc}")

  with open(output_path, "a", encoding="utf-8") as f:
      f.write(f"MODEL : {model} \n")
      f.write(f"OPINION : {opignion} \n")
      f.write("="*10 + f"\n, PAGE : {i} \n" + "="*10 + "\n\n")
      f.write(str(txt) + "\n")
      f.close()
  print(f"page {i} dans le fichier : {output_path}")



def manager(txt, infos,i):
  '''
  Cette classe permet de manager le texte de la page en fonction du score donné par MetricsCerWer.
  Si le score est "dirty" ou "medium", on envoie le texte a corriger a l'LLM, sinon on écrit le texte directement dans un fichier de sortie.
  '''
  global api, model
  score = getLabelScore(txt)
  
  if score == 'dirty':
      if api:
          Llm.llmCorrectionMistral(infos, txt, i)
      else:
          Llm.llmCorrectionLocal(infos, txt, i, model)
  elif score == 'medium':
      if api:
          Llm.llmCorrectionMistral(infos, txt, i)
      else:
          Llm.llmCorrectionLocal(infos, txt, i, model)
  elif score == 'clean':
     write(txt, i, "fidele")
  

def launchPostOcr(url):
  '''
  Methde principale qui lance le post OCR.
  Elle prend en entrée un url d'article, 
  extrait les informations de l'article, 
  télécharge le pdf, 
  récupère le nombre de page du pdf, et pour chaque page, 
  elle récupère le texte de la page et le manager en fonction du score donné par MetricsCerWer.
  '''
  global model, api
  i = 0
  print(api, "api dans launchPostOcr")

  if not url:
      url = input("Lien de l'article a travailler : ")
  print(f"[LLM] - url : {url} ")

  MetricsCerWer.configureArticleLanguage(url)
  infos = ContexteHelper.startExtraction(url) 

  PdfDownloader.pdfStarter(url) #Téléchargement du pdf
  NAME = PdfDownloader.getLastName() #Récupération du nom donnée au pdf
  NBRPAGE = PdfChunking.nbrPage(NAME)  #Récupération du nombre de page

  for i in range(0, NBRPAGE):
    print(f"\n\n Vous travaillez avec le model : {model}")
    print("+"*30, f"ANALYSE EN COURS DE LA PAGE : {i}/{NBRPAGE}", "+"*30)

    txt = PdfChunking.showText(NAME, i)
    manager(txt, infos, i)




def main():
  global model, api

  print(""" 
█████   █████ ██████████ ███████████   █████ ███████████   █████████    █████████     ██████   ██████  ████████    █████████ 
▒▒███   ▒▒███ ▒▒███▒▒▒▒▒█▒▒███▒▒▒▒▒███ ▒▒███ ▒█▒▒▒███▒▒▒█  ███▒▒▒▒▒███  ███▒▒▒▒▒███   ▒▒██████ ██████  ███▒▒▒▒███  ███▒▒▒▒▒███
 ▒███    ▒███  ▒███  █ ▒  ▒███    ▒███  ▒███ ▒   ▒███  ▒  ▒███    ▒███ ▒███    ▒▒▒     ▒███▒█████▒███ ▒▒▒    ▒███ ███     ▒▒▒ 
 ▒███    ▒███  ▒██████    ▒██████████   ▒███     ▒███     ▒███████████ ▒▒█████████     ▒███▒▒███ ▒███    ██████▒ ▒███         
 ▒▒███   ███   ▒███▒▒█    ▒███▒▒▒▒▒███  ▒███     ▒███     ▒███▒▒▒▒▒███  ▒▒▒▒▒▒▒▒███    ▒███ ▒▒▒  ▒███   ▒▒▒▒▒▒███▒███         
  ▒▒▒█████▒    ▒███ ▒   █ ▒███    ▒███  ▒███     ▒███     ▒███    ▒███  ███    ▒███    ▒███      ▒███  ███   ▒███▒▒███     ███
    ▒▒███      ██████████ █████   █████ █████    █████    █████   █████▒▒█████████     █████     █████▒▒████████  ▒▒█████████ 
     ▒▒▒      ▒▒▒▒▒▒▒▒▒▒ ▒▒▒▒▒   ▒▒▒▒▒ ▒▒▒▒▒    ▒▒▒▒▒    ▒▒▒▒▒   ▒▒▒▒▒  ▒▒▒▒▒▒▒▒▒     ▒▒▒▒▒     ▒▒▒▒▒  ▒▒▒▒▒▒▒▒    ▒▒▒▒▒▒▒▒▒ """) 
  
  print("\n\n\nQue voulez vous faire ?\n1 - Lancer le post OCR\n2 - Téléchargement d'un pdf de la M3C\n3 - Quitter")
  choix = input("Entrez votre choix : ").lower()    
  
  match choix:
  
    case "1":
      launchPostOcr("")
  
    case "2":
      url = input("Entrez le lien du pdf à télécharger : ")
      PdfDownloader.pdfStarter(url)
  
    case "3":
      exit()
  
    case "local":
        launchPostOcr("https://m3c.universita.corsica/s/fr/item/58")

    case "api":
        api = True
        print(api, "api activé")
        launchPostOcr("https://m3c.universita.corsica/s/fr/item/58")

    case _:
      print("Choix invalide. Veuillez réessayer.")

                                                                                                                         
#Lancement méthode principale attention a la chauffe
#launchPostOcr("https://m3c.universita.corsica/s/fr/item/73905")
#launchPostOcr("https://m3c.universita.corsica/s/fr/item/58")
#print(ContexteHelper.startExtraction("https://m3c.universita.corsica/s/fr/item/58"))

if __name__ == "__main__":
    main()