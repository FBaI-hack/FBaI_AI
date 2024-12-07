import uuid
import time
import json
import os
import requests
import boto3


def naver_ocr(file_name: str, file_key: str) -> str:
    """
    NAVER OCR API 기반으로 TEXT 추출하는 로직
    - return : jpg format 파일에 대한 OCR API 응답값
    """
    NAVER_OCR_URL = os.environ.get("NAVER_OCR_URL")
    NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")
    S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")

    s3_client = boto3.client('s3')
    s3_response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=file_key)
    file_content = s3_response['Body'].read()
    
    headers = {
        "X-OCR-SECRET": NAVER_CLIENT_SECRET
    }

    request_json = {
      "images": [
          {
          "format": "jpg",
          "name": file_name
          }
      ],
      "version": "V2",
      "requestId": str(uuid.uuid4()),
      "timestamp": int(round(time.time() * 1000))
    }

    payload = {
        'message': json.dumps(request_json).encode('UTF-8')
    }

    files = {
        "file": (file_name, file_content)
    }

    response = requests.request(
        method="POST", url=NAVER_OCR_URL, headers=headers, data=payload, files=files
    )

    return get_ocr_result(response)

def extract_key_value_pairs(json_string: str, keys: list) -> dict:
    """
    API 응답값에서 select한 key, value 만 추출하는 로직
    - return : dict에서 select한 key, value 쌍
    """
    data_dict = json.loads(json_string)
    extract_data_dict = {
        key: data_dict[key] for key in keys if key in data_dict
    }
    return extract_data_dict

def get_ocr_result(response: json) -> str:
    """
    API 응답값에서 status_code 기반으로 결과값 반환하는 로직
    - return : 추출된 text 값 or Exception 처리
    """
    if response.status_code == 200:
        ocr_result = response.json()
        extracted_text = " ".join(
            [field["inferText"] for field in ocr_result["images"][0]["fields"]]
        )
        return extracted_text
    else:
        keys_to_extract = [
            "code", "message", "traceId", "timestamp"
        ]
        response_selected_text = extract_key_value_pairs(
            json_string = response.text, 
            keys = keys_to_extract
        )
        raise Exception(f"OCR API 요청 실패: {response.status_code}, {response_selected_text}")
