from promptflow.tracing import start_trace
start_trace()

import os
from dotenv import load_dotenv
load_dotenv()

from promptflow.core import Prompty, AzureOpenAIModelConfiguration

model_config = AzureOpenAIModelConfiguration(
    azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

prompty = Prompty.load("chat.prompty", model={'configuration': model_config})
result = prompty(
    chat_history=[
        {"role": "user", "content": "Does Azure OpenAI support customer managed keys?"},
        {"role": "assistant", "content": "Yes, customer managed keys are supported by Azure OpenAI."}
    ],
    chat_input="Do other Azure AI services support this too?")

print(result)