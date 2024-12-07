from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import os


def is_fraud_text(text: str) -> bool:
    """
    키워드 기반 사기 여부 판단 로직
    - return : 특정 키워드 포함 여부
    """
    fraud_keywords = ["사기", "계약금", "선불", "직거래", "선입금"]
    return any(keyword in text for keyword in fraud_keywords)

def invoke_chain(suspicious_texts: str) -> str:
  """
  LLM 기반 fraud detection assistant chain 생성 로직
  - return : chain 으로 invoke 된 response
  """
  OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
  llm = ChatOpenAI(api_key=OPENAI_API_KEY)
  
  explanation_prompt = ChatPromptTemplate.from_messages([
      ("system", "You are a helpful, professional assistant named FBaI-Bot. \
      You are an expert fraud detection assistant. \
      Analyze the suspicious texts provided below and explain why they may indicate fraud. \
      Answer in Korean."),
      ("user", "{suspicious_texts}")
  ])
  
  output_parser = StrOutputParser()
  chain = explanation_prompt | llm | output_parser
  chain_reponse = chain.invoke({
      "suspicious_texts": suspicious_texts
  })

  return chain_reponse
