from fastapi import FastAPI, UploadFile, File
from typing import List
from ocr import *
from lang_chain import *


app = FastAPI(
  title="FBaI Server",
  version="1.0",
  description="FBaI : detect fraud by images",
)

@app.post("/detect_fraud_images")
async def detect_fraud_images(files: List[UploadFile] = File(...)):
    """
    이미지 기반 사기 여부 판단 로직
    - return : 각 이미지에 대한 사기 판단 예측 결과값
    """

    fraud_results = []
    for file in files:
        try:
            
            # 업로드 된 파일 임시 저장
            file_path = f"/tmp/{file.filename}"
            with open(file_path, "wb") as f:
                f.write(await file.read())
            
            # naver ocr api 기반으로 text 추출
            extracted_text = naver_ocr(
                file_path=file_path, 
                file_name=file.filename
            )
            
            # 사기 여부 판단 및 판단의 근거 도출
            is_fraud = is_fraud_text(extracted_text)
            explanation = invoke_chain(suspicious_texts=extracted_text) if is_fraud else None
                
            # 사기 판단 결과에 대한 json array 생성
            fraud_results.append({
                "file_name": file.filename,
                "extracted_text": extracted_text.strip(),
                "fraud_result": is_fraud,
                "fraud_explanation" : explanation
            })
        
        except Exception as e:
            fraud_results.append({
                "file_name": file.filename,
                "error": str(e)
            })

    return {"results": fraud_results} 

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)