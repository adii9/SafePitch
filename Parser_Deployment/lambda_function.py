import os
import io
import json
import asyncio
import base64
import boto3
from botocore.exceptions import ClientError
from llama_parse import LlamaParse
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account

# Initialize AWS clients outside the handler to reuse connections
secrets_client = boto3.client('secretsmanager')
lambda_client = boto3.client('lambda')

def get_google_credentials():
    """Fetch the service_account.json content from AWS Secrets Manager."""
    secret_name = os.environ.get("GOOGLE_CREDENTIALS_SECRET_NAME", "GoogleDriveServiceAccount")
    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        creds_info = json.loads(response['SecretString'])
        return creds_info
    except ClientError as e:
        print(f"Error retrieving secret {secret_name}: {e}")
        raise e

def get_drive_service(creds_info):
    """Authenticate and build the Google Drive API service using dict credentials."""
    creds = service_account.Credentials.from_service_account_info(
        creds_info,
        scopes=['https://www.googleapis.com/auth/drive.readonly']
    )
    return build('drive', 'v3', credentials=creds)

def download_file_from_drive(file_id, service):
    """Download or export the Google Drive file to /tmp/"""
    file_path = f"/tmp/temp_{file_id}.pdf"
    
    try:
        # First, query the file's metadata to find its mimeType
        file_metadata = service.files().get(fileId=file_id, fields='mimeType, name').execute()
        mime_type = file_metadata.get('mimeType', '')
        file_name = file_metadata.get('name', '')
        print(f"File found: {file_name} (MIME type: {mime_type})")

        # If it is a native Google Workspace document (Docs, Sheets, Slides)
        if mime_type.startswith('application/vnd.google-apps.'):
            print("Exporting Google Workspace document as PDF...")
            request = service.files().export_media(fileId=file_id, mimeType='application/pdf')
        else:
            # If it is a binary file (PDF, PPTX, DOCX, Images, etc.)
            print("Downloading binary file directly...")
            request = service.files().get_media(fileId=file_id)

        # Execute the download/export
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            print(f"Download {int(status.progress() * 100)}%.")
        
        fh.seek(0)
        with open(file_path, "wb") as f:
            f.write(fh.read())
            
        print("Download complete.")
        return file_path

    except Exception as e:
        print(f"Error downloading file {file_id}: {str(e)}")
        raise e

def download_file_from_s3(s3_key):
    """Download a file from S3 to /tmp/"""
    import uuid
    s3 = boto3.client('s3')
    bucket = os.environ.get('S3_BUCKET_NAME')
    if not bucket:
        raise ValueError("S3_BUCKET_NAME environment variable not set")

    # Determine file extension from the key
    ext = s3_key.split('.')[-1] if '.' in s3_key else 'pdf'
    temp_path = f"/tmp/{uuid.uuid4().hex}.{ext}"

    s3.download_file(bucket, s3_key, temp_path)
    print(f"Downloaded s3://{bucket}/{s3_key} to {temp_path}")
    return temp_path


def decode_pdf_from_base64(pdf_base64, pdf_name):
    """Decode base64 PDF content and save to /tmp"""
    import uuid
    temp_path = f"/tmp/{uuid.uuid4().hex}_{pdf_name}"
    try:
        pdf_bytes = base64.b64decode(pdf_base64)
        with open(temp_path, 'wb') as f:
            f.write(pdf_bytes)
        print(f"PDF decoded: {temp_path}, size: {len(pdf_bytes)} bytes")
        return temp_path
    except Exception as e:
        print(f"Failed to decode base64 PDF: {e}")
        raise


def build_response(status_code, body_dict):
    """Build a response with proper CORS headers for API Gateway."""
    body = json.dumps(body_dict)
    # CORS headers - allow the origin dynamically or use * for all
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key",
        "Access-Control-Allow-Methods": "OPTIONS,POST",
        "Content-Type": "application/json"
    }
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": body
    }

def lambda_handler(event, context):
    print("Received event:", event)

    # 1. Extract event inputs
    # Handle either API Gateway string payload or direct JSON payload
    if isinstance(event.get('body'), str):
        try:
            body = json.loads(event['body'])
        except Exception:
            body = {}
    else:
        body = event

    company_name = body.get('company_name', 'Unknown')
    email_body = body.get('email_body', '')
    tenant_slug = body.get('tenant_slug', 'default')

    # Check which input mode we're using
    file_id = body.get('file_id')
    s3_key = body.get('s3_key')
    pdf_base64 = body.get('pdf_base64')

    # 2. Get environment variables
    llama_key = os.environ.get("LLAMA_CLOUD_API_KEY", "").strip()
    crewai_lambda_name = os.environ.get("CREWAI_LAMBDA_NAME")

    if not llama_key:
        return build_response(500, {"error": "Missing LLAMA_CLOUD_API_KEY"})
    if not crewai_lambda_name:
        return build_response(500, {"error": "Missing CREWAI_LAMBDA_NAME"})

    temp_file_path = None

    try:
        # 3. Retrieve file — three input modes supported
        if pdf_base64:
            # Mode 1: Base64 PDF sent directly from the frontend
            print("Decoding base64 PDF...")
            temp_file_path = decode_pdf_from_base64(pdf_base64, body.get('pdf_name', 'upload.pdf'))
        elif s3_key:
            # Mode 2: File already uploaded to S3 via presigned URL
            print(f"Downloading file from S3: {s3_key}")
            temp_file_path = download_file_from_s3(s3_key)
        elif file_id:
            # Mode 3: Google Drive file ID (existing flow)
            print("Fetching credentials from Secrets Manager...")
            creds_info = get_google_credentials()
            service = get_drive_service(creds_info)
            print(f"Downloading file {file_id} from Drive...")
            temp_file_path = download_file_from_drive(file_id, service)
        else:
            return build_response(400, {"error": "Missing file_id, s3_key, or pdf_base64"})

        # 5. Parse PDF to Markdown using LlamaParse
        print(f"Parsing {company_name} PDF to Markdown...")
        parser = LlamaParse(
            api_key=llama_key,
            result_type="markdown",
            verbose=True
        )
        
        # We must use asyncio.run to execute the async LlamaParse function inside a sync Lambda
        documents = asyncio.run(parser.aload_data(temp_file_path))
        pitch_deck_markdown = "\n".join([doc.text for doc in documents])

        # 6. Prepare Payload for Lambda 2 (CrewAI)
        payload_for_crewai = {
            "tenant_slug": tenant_slug,
            "company_name": company_name,
            "email_body": email_body,
            "pitch_deck_content": pitch_deck_markdown
        }
        
        # Convert to string and measure payload size
        payload_str = json.dumps(payload_for_crewai)
        payload_size_kb = len(payload_str.encode('utf-8')) / 1024
        print(f"Payload size: {payload_size_kb:.2f} KB")

        if payload_size_kb > 256:
            print("WARNING: Payload exceeds Lambda Async limit of 256KB! You may need to store it in S3 instead.")

        # 7. Invoke Lambda 2 Asynchronously (Event)
        print(f"Invoking CrewAI Lambda: {crewai_lambda_name}")
        response = lambda_client.invoke(
            FunctionName=crewai_lambda_name,
            InvocationType='Event', # Crucial: This makes the call async
            Payload=payload_str
        )

        print(f"Successfully triggered CrewAI Lambda. Status code: {response.get('StatusCode')}")

        return build_response(200, {'message': f'Successfully parsed document and triggered CrewAI for {company_name}'})

    except Exception as e:
        print(f"FAILED: {str(e)}")
        return build_response(500, {'error': str(e)})

    finally:
        # Always clean up the temp file in Lambda /tmp directory
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
