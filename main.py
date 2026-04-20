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

import os
import re
from datetime import datetime
from ollama import chat
from ollama import ChatResponse

modelListe = ['mistral', 'llama3:8b', 'qwen3-vl:8b']
model = modelListe[1] #Choix du modèle

CheckModel.CheckModel(model)
MetricsCerWer.configure_model(model)
    

def GetLabelScore(txt):
  details = MetricsCerWer.score_details(txt)
  print("algo_score:", round(details["algo_score"], 3))
  print("llm_label:", details["llm_label"])
  print("final_label_value:", details["final_label_value"])
  return details["final_label_value"]
   


def llmCorrection(infos, txt, i):
  '''
  Dico : titre, description, date, couverture_temporelle, langue
  '''
  
  response: ChatResponse = chat(model=model, messages=[
    {
      'role': 'system',
      'content':SystemPrompt.prompt2(infos)
      },
    {
      'role': 'user',
      'content': f"TEXTE A CORRIGER : {txt}"
    }
  ])

  #print(response.message.content)
  txtCorrection = str(response.message.content)
  with open("log.txt", "a", encoding="utf-8") as f:
    f.write(f"page {i} : {txt} \n\n")
  f.close()
  llmVerification(txt, txtCorrection, i)

def llmVerification(txt, txtCorrection, i):
   response: ChatResponse = chat(model=model, messages=[
    {
      'role': 'system',
      'content':SystemPrompt.promptVerification()
      },
    {
      'role': 'user',
      'content': f"TEXTE ORIGINAL : {txt} \n\n TEXTE CORRIGE : {txtCorrection}"
    }
  ])
   print(response.message.content)
   reponse = str(response.message.content).lower()
   write(txtCorrection, i, reponse)


def write(txt, i, opignion):
  global model
  Suffilename = datetime.now().strftime("pdf-%d-%m-%H")
  
  safe_model = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", str(model)).strip(" .")
  
  if not safe_model:
      safe_model = "model"
  
  filename = f"{safe_model}{Suffilename}"
  
  project_root = os.path.dirname(os.path.abspath(__file__))
  output_dir = os.path.join(project_root, "output")
  os.makedirs(output_dir, exist_ok=True)

  output_path = os.path.join(output_dir, filename + '.txt')
  
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
  score = GetLabelScore(txt)
  
  if score == 'dirty':
      llmCorrection(infos, txt, i)
  elif score == 'medium':
      llmCorrection(infos, txt, i)
  elif score == 'clean':
     write(txt, i, "fidele")
  

def LaunchPostOcr(url):
  '''
  Methde principale qui lance le post OCR.
  Elle prend en entrée un url d'article, 
  extrait les informations de l'article, 
  télécharge le pdf, 
  récupère le nombre de page du pdf, et pour chaque page, 
  elle récupère le texte de la page et le manager en fonction du score donné par MetricsCerWer.
  '''
  global model
  i = 0
  
  if not url:
      url = input("Lien de l'article a travailler : ")
  print(f"[LLM] - url : {url} ")

  MetricsCerWer.configure_article_language(url)
  infos = ContexteHelper.startExtraction(url) 

  PdfDownloader.PdfStarter(url) #Téléchargement du pdf
  name = PdfDownloader.GetLastName() #Récupération du nom donnée au pdf
  
  NBRPAGE = PdfChunking.NbrPage(name)  #Récupération du nombre de page

  for i in range(0, NBRPAGE):
    print("\n\n")
    print("Vous travaillez avec le model : ", model)
    print("+"*30)
    print(f"ANALYSE EN COURS DE LA PAGE : {i}/{NBRPAGE}")
    print("+"*30)
    txt = PdfChunking.ShowText(name, i)
    manager(txt, infos, i)
  print("fini")


def main():
  global model

  print(""" █████   █████ ██████████ ███████████   █████ ███████████   █████████    █████████     ██████   ██████  ████████    █████████ 
▒▒███   ▒▒███ ▒▒███▒▒▒▒▒█▒▒███▒▒▒▒▒███ ▒▒███ ▒█▒▒▒███▒▒▒█  ███▒▒▒▒▒███  ███▒▒▒▒▒███   ▒▒██████ ██████  ███▒▒▒▒███  ███▒▒▒▒▒███
 ▒███    ▒███  ▒███  █ ▒  ▒███    ▒███  ▒███ ▒   ▒███  ▒  ▒███    ▒███ ▒███    ▒▒▒     ▒███▒█████▒███ ▒▒▒    ▒███ ███     ▒▒▒ 
 ▒███    ▒███  ▒██████    ▒██████████   ▒███     ▒███     ▒███████████ ▒▒█████████     ▒███▒▒███ ▒███    ██████▒ ▒███         
 ▒▒███   ███   ▒███▒▒█    ▒███▒▒▒▒▒███  ▒███     ▒███     ▒███▒▒▒▒▒███  ▒▒▒▒▒▒▒▒███    ▒███ ▒▒▒  ▒███   ▒▒▒▒▒▒███▒███         
  ▒▒▒█████▒    ▒███ ▒   █ ▒███    ▒███  ▒███     ▒███     ▒███    ▒███  ███    ▒███    ▒███      ▒███  ███   ▒███▒▒███     ███
    ▒▒███      ██████████ █████   █████ █████    █████    █████   █████▒▒█████████     █████     █████▒▒████████  ▒▒█████████ 
     ▒▒▒      ▒▒▒▒▒▒▒▒▒▒ ▒▒▒▒▒   ▒▒▒▒▒ ▒▒▒▒▒    ▒▒▒▒▒    ▒▒▒▒▒   ▒▒▒▒▒  ▒▒▒▒▒▒▒▒▒     ▒▒▒▒▒     ▒▒▒▒▒  ▒▒▒▒▒▒▒▒    ▒▒▒▒▒▒▒▒▒ """) 
  
  print("\n\n\nQue voulez vous faire ?\n1 - Lancer le post OCR\n2 - Téléchargement d'un pdf de la M3C\n3 - Quitter")
  choix = input("Entrez votre choix : ")    
  
  match choix:
  
    case "1":
      LaunchPostOcr("")
  
    case "2":
      url = input("Entrez le lien du pdf à télécharger : ")
      PdfDownloader.PdfStarter(url)
  
    case "3":
      exit()
  
    case "test":
        LaunchPostOcr("https://m3c.universita.corsica/s/fr/item/58")
    case _:
      print("Choix invalide. Veuillez réessayer.")

                                                                                                                         
#Lancement méthode principale attention a la chauffe
#LaunchPostOcr("https://m3c.universita.corsica/s/fr/item/73905")
#LaunchPostOcr("https://m3c.universita.corsica/s/fr/item/58")
#print(ContexteHelper.startExtraction("https://m3c.universita.corsica/s/fr/item/58"))

if __name__ == "__main__":
    main()