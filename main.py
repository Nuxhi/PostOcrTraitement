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
from ollama import chat
from ollama import ChatResponse

model = 'Mistral'

CheckModel.CheckModel(model)
    
def llm(link):
  if not link:
      link = input("Lien de l'article a travailler : ")
  print(f"[LLM] - link : {link} ")

  print("[MAIN] - infos")
  infos = ContexteHelper.startExtraction(link)
  
  print("[MAIN] -> PdfHelper")
  PdfHelper.PdfStarter(link)
  name = PdfHelper.GetLastName()
  print("[MAIN] - LLM EN COURS")
  #PdfChunking.chunking(PdfHelper.GetLastName)
  '''
  Dico : titre, description, date, couverture_temporelle, langue
  '''
  
  response: ChatResponse = chat(model='Mistral', messages=[
    {
      'role': 'system',
      'content':SystemPrompt.prompt() 
    },
    {
      'role': 'system',
      'content':"Pour t'aider, tu as les informations suivante a disposition : "
      
      f"Titre : {infos['titre']}" 
      f"description : {infos['description']}"
      f"date : {infos['date']}"
      f"couverture temporelle : {infos['couverture_temporelle']}"
      f"langue : {infos['langue']}"
      "Tu corrige le texte apres le mot 'TEXTE A CORRIGER : ' et tu met ta correction apres 'TEXTE CORRIGER :'"
    },
    {
      'role': 'user',
      'content': "TEXTE A CORRIGER : fioi sia1TW debitori di alcuni cardi~ edi alcune di-' lucida;;ioni ai canli medesimi, alla cortesïadi ALES 5AXDRO AR:lIAXD di Ajaccio, già Sotto-Prefetto di"
      "TEXTE CORRIGER : ",
    },
  ])
  print(response['message']['content'])
  # or access fields directly from the response object
  print(response.message.content)


llm("https://m3c.universita.corsica/s/fr/item/15")

