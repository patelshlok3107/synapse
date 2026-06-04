import os
from openai import OpenAI

client = OpenAI(
  base_url = "https://integrate.api.nvidia.com/v1",
  api_key = "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"
)

completion = client.chat.completions.create(
  model="meta/llama-3.1-8b-instruct",
  messages=[{"role":"user","content":"Hi"}],
  temperature=0.2,
  top_p=0.7,
  max_tokens=10,
)

print(completion.choices[0].message.content)
