
import os

from ollama import chat
from ollama import ChatResponse
from mistralai.client import Mistral

import app.SystemPrompt as SystemPrompt
from main import write



def llmCorrectionMistral(infos, txt, i):
    '''
    Dico : titre, description, date, couverture_temporelle, langue
    '''
    client = Mistral(api_key=os.getenv("MISTRAL_API_KEY", ""))

    res = client.chat.complete(
        model="mistral-small-latest",
        messages=[
        {
            "content": SystemPrompt.prompt2(infos),
            "role": "system",
        },
        {
            "content": f"TEXTE A CORRIGER : {txt}",
            "role": "user",
        }
    ], stream=False)

    print(res) # a RETIRER PLUS TARD
    txtCorrection = str(res)

    # Debug : écriture du texte original dans un fichier de log
    with open("log.txt", "a", encoding="utf-8") as f:
        f.write(f"page {i} : {txt} \n\n")
    f.close()
    #############################################################

    llmVerificationMistral(txt, txtCorrection, i)


def llmVerificationMistral(txt, txtCorrection, i):
    client = Mistral(api_key=os.getenv("MISTRAL_API_KEY", ""))
    response = client.chat(
     [
        {
          'role': 'system',
          'content':SystemPrompt.promptVerification()
        },
        {
          'role': 'user',
          'content': f"TEXTE ORIGINAL : {txt} \n\n TEXTE CORRIGE : {txtCorrection}"
        }
     ]
      )
    print(response.message.content)
    reponse = str(response.message.content).lower()
    write(txtCorrection, i, reponse)



################################################
#### Tourne avec des models locaux (ollama) ####
################################################

def llmCorrectionLocal(infos, txt, i, model):
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

  print(response.message.content)
  txtCorrection = str(response.message.content)
  # Debug : écriture du texte original dans un fichier de log
  with open("log.txt", "a", encoding="utf-8") as f:
    f.write(f"page {i} : {txt} \n\n")
  f.close()
  llmVerificationLocal(txt, txtCorrection, i, model)


def llmVerificationLocal(txt, txtCorrection, i, model):
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