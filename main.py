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
import app.PdfHelper as PdfHelper
import app.PdfChunking as PdfChunking
import app.MetricsCerWer as MetricsCerWer

import time
import os
from ollama import chat
from ollama import ChatResponse


model = 'Mistral'

CheckModel.CheckModel(model)
    

# def chunking(pdfname):
#     #Path()
#     print(pdfname)
#     reader = PdfReader(pdfname+'.pdf')
#     for i in range(NbrPage(pdfname)):
#         try:
#             ShowText(pdfname, i)
#         except NameError as e:
#             return e


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
  
  
  system_content = (
      SystemPrompt.prompt() + "\n\n" +
      "Pour t'aider, tu as les informations suivante a disposition : "
      f"Titre : {infos['titre']} "
      f"description : {infos['description']} "
      f"date : {infos['date']} "
      f"couverture temporelle : {infos['couverture_temporelle']} "
      f"langue : {infos['langue']} \n\n"
      "Répond STRICTEMENT sous la forme suivante :\n"
      "<texte corrigé uniquement>\n"
      "Ne rajoute aucun commentaire."
      )

  response: ChatResponse = chat(model='Mistral', messages=[
    {
      'role': 'system',
      'content':system_content,
      'role': 'user',
      'content': f"TEXTE A CORRIGER : {txt}"
    }
  ])
  print(response.message.content)
  write(response.message.content, i)


def write(txt, i):
  output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "myfile.txt")
  with open(output_path, "a", encoding="utf-8") as f:
      f.write("="*10 + f"\n, PAGE : {i} \n" + "="*10)
      f.write(txt + "\n")


def manager(txt, infos,i):
  score = GetLabelScore(txt)
  
  if score == 'dirty':
      llmCorrection(infos, txt, i)
  elif score == 'medium':
      llmCorrection(infos, txt, i)
  elif score == 'clean':
     write(txt, i)
  

def LaunchPostOcr(url):
  
  i:int = 0

  if not url:
      url = input("Lien de l'article a travailler : ")
  print(f"[LLM] - url : {url} ")

  
  infos = ContexteHelper.startExtraction(url) 
  PdfHelper.PdfStarter(url) #Téléchargement du pdf
  name = PdfHelper.GetLastName() #Récupération du nom donnée au pdf

  NBRPAGE = PdfChunking.NbrPage(name)  #Récupération du nombre de page

  for i in range(0, NBRPAGE):
    print("+"*30)
    print(f"ANALYSE EN COURS DE LA PAGE : {i}/{NBRPAGE}")
    print("+"*30)
    #time.sleep(1)
    txt = PdfChunking.ShowText(name, i)
    manager(txt, infos, i)
  print("fini")




##Lancement méthode principale attention a la chauffe
LaunchPostOcr("https://m3c.universita.corsica/s/fr/item/227")