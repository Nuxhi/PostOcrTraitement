'''
POST OCR to correction with LLM
APP VERSION : 0.1
STATE : ALPHA
'''

'''
Item : https://m3c.universita.corsica/s/fr/item/15
'''

import app.CheckModel as CheckModel

from ollama import chat
from ollama import ChatResponse

model = 'Mistral'

CheckModel.CheckModel(model)
    
  

response: ChatResponse = chat(model='Mistral', messages=[
  {
    'role': 'system',
    'content':'tu répond simplement aux questions.'  
  },
  {
    'role': 'user',
    'content': "Comment tu vas ? ",
  },
])
print(response['message']['content'])
# or access fields directly from the response object
print(response.message.content)