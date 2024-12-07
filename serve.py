from fastapi import FastAPI, UploadFile, File, Form, UploadFile
from typing import List, Annotated
from ocr import *
from lang_chain import *
from mangum import Mangum
import boto3
import requests
import uuid

app = FastAPI(
  title="FBaI Server",
  version="1.0",
  description="FBaI : detect fraud by images",
)

lambda_handler = Mangum(app)

@app.post("/detect_fraud_images")
async def detect_fraud_images(files: List[UploadFile] = File(...)):
    """
    이미지 기반 사기 여부 판단 로직
    - return : 각 이미지에 대한 사기 판단 예측 결과값
    """

    fraud_results = []
    for file in files:
        try:

            s3_client = boto3.client('s3')
            S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
            file_key = f"uploads/{file.filename}"
            s3_client.upload_fileobj(file.file, S3_BUCKET_NAME, file_key)

            # naver ocr api 기반으로 text 추출
            extracted_text = naver_ocr(
                file_name=file.filename,
                file_key=file_key
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


@app.post("/check_spam_number")
async def check_spam_number(number: Annotated[str, Form()]):

    CL_AUTH_KEY = os.environ.get("CL_AUTH_KEY")

    check_spam_number_url = "https://apick.app/rest/check_spam_number"
    
    headers = {
        "CL_AUTH_KEY":CL_AUTH_KEY
    }
    
    payload = {
        "number": number
    }
    
    response = requests.request(
        method="POST", url=check_spam_number_url, headers=headers, data=payload
    )
    
    parsed_response = json.loads(response.text)

    return {
            "status_code": response.status_code,
            "results": parsed_response["data"]
          }


@app.post("/check_phone_valid")
async def check_phone_valid(number: Annotated[str, Form()]):

    CL_AUTH_KEY = os.environ.get("CL_AUTH_KEY")
    
    check_phone_valid_url = "https://apick.app/rest/check_phone_valid"
    
    headers = {
        "CL_AUTH_KEY":CL_AUTH_KEY
    }
    
    payload = {
        "number": number
    }
    
    response = requests.request(
        method="POST", url=check_phone_valid_url, headers=headers, data=payload
    )
    
    parsed_response = json.loads(response.text)

    return {
            "status_code": response.status_code,
            "results": parsed_response["data"]
          }

@app.post("/check_email_valid")
async def check_email_valid(email: Annotated[str, Form()]):

    CL_AUTH_KEY = os.environ.get("CL_AUTH_KEY")
    
    check_email_valid_url = "https://apick.app/rest/check_email_valid"
    
    headers = {
        "CL_AUTH_KEY":CL_AUTH_KEY
    }
    
    payload = {
        "email": email
    }
    
    response = requests.request(
        method="POST", url=check_email_valid_url, headers=headers, data=payload
    )
    
    parsed_response = json.loads(response.text)

    return {
            "status_code": response.status_code,
            "results": parsed_response["data"]
          }


@app.post("/account_realname")
async def account_realname(account_num: Annotated[str, Form()], bank_name: Annotated[str, Form()]):

    CL_AUTH_KEY = os.environ.get("CL_AUTH_KEY")
    
    account_realname_url = "https://apick.app/rest/account_realname"
    
    headers = {
        "CL_AUTH_KEY":CL_AUTH_KEY
    }
    
    payload = {
        "account_num": account_num,
        "bank_name": bank_name
    }
    
    response = requests.request(
        method="POST", url=account_realname_url, headers=headers, data=payload
    )
    
    parsed_response = json.loads(response.text)

    return {
            "status_code": response.status_code,
            "results": parsed_response["data"]
          }

@app.post("/google_lens_search")
async def google_lens_search(file: UploadFile = File(...)):

    CL_AUTH_KEY = os.environ.get("CL_AUTH_KEY")
    s3_client = boto3.client('s3')
    S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")

    file_id = str(uuid.uuid4())
    origin_file_key = f"google_lens_search/{file_id}/origin/{file.filename}"
    s3_client.upload_fileobj(file.file, S3_BUCKET_NAME, origin_file_key)

    s3_response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=origin_file_key)
    file_content = s3_response['Body'].read()
    
    files = {
        "image": (file.filename, file_content)
    }

    google_lens_search_url = "https://apick.app/rest/google_lens_search"
    
    headers = {
        "CL_AUTH_KEY":CL_AUTH_KEY
    }

    response = requests.request(
        method="POST", url=google_lens_search_url, headers=headers, files=files
    )
    
    parsed_response = json.loads(response.text)
    top_item = parsed_response["data"]["items"][:5]
    

    compare_image = []
    for item in top_item:
      
      image_url = item["img"]
      response = requests.request(
          method="GET", url=image_url
      )

      image_data = response.content
      image_name = image_url.split("q=")[-1]
      
      search_file_key = f"google_lens_search/{file_id}/search/{image_name}"

      s3_client.put_object(
          Bucket=S3_BUCKET_NAME,
          Key=search_file_key,
          Body=image_data,
          ContentType="image/jpeg" 
      )

      search_s3_response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=search_file_key)
      search_file_content = search_s3_response['Body'].read()
      compare_image.append([image_name,search_file_content])

    image_similarity_url = "https://apick.app/rest/image_similarity"

    origin_s3_response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=origin_file_key)
    origin_file_content = origin_s3_response['Body'].read()
  
    
    files = {
        "image": (origin_file_key.split("/")[-1], origin_file_content),
        "compare_image1": (compare_image[0][0], compare_image[0][1]),  
        "compare_image2": (compare_image[1][0], compare_image[1][1]),  
        "compare_image3": (compare_image[2][0], compare_image[2][1]), 
        "compare_image4": (compare_image[3][0], compare_image[3][1]), 
        "compare_image5": (compare_image[4][0], compare_image[4][1])
    }


    response = requests.request(
        method="POST", url=image_similarity_url, headers=headers, files=files
    )

    parsed_response = json.loads(response.text)

    return {
            "status_code": response.status_code,
            "results": parsed_response["data"]
          }



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)