import os
import json
import sys
import boto3
from botocore.exceptions import ClientError
import uuid
from datetime import datetime

# --- LAMBDA FIX ---
# AWS Lambda environment is read-only except for /tmp.
# CrewAI attempts to create cache/db directories in the user's home directory.
# We must override HOME to point to /tmp BEFORE importing CrewAI.
os.environ["HOME"] = "/tmp"

# We change directory to /tmp so that any relative path writes go to /tmp
os.chdir('/tmp')

# Wait to import our flow until after chdir if necessary, or import normally from src.
# We must append the task root to sys.path since we changed directories.
sys.path.insert(0, os.environ.get("LAMBDA_TASK_ROOT", ""))
# ------------------

from safepitch.main import SafepitchFlow

# AWS Clients built into Lambda
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

DB_LOCAL_DIR = '/tmp/.crewai'
DB_LOCAL_PATH = f'{DB_LOCAL_DIR}/flows.db'
DB_S3_KEY = 'crewai_state/flows.db'

def sync_db_from_s3(bucket_name):
    os.makedirs(DB_LOCAL_DIR, exist_ok=True)
    try:
        s3_client.download_file(bucket_name, DB_S3_KEY, DB_LOCAL_PATH)
        print(f"Successfully downloaded flows.db from S3 bucket: {bucket_name}")
    except ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("flows.db does not exist in S3 yet. A new one will be created locally.")
        else:
            print(f"Error downloading from S3: {e}")

def sync_db_to_s3(bucket_name):
    if os.path.exists(DB_LOCAL_PATH):
        try:
            s3_client.upload_file(DB_LOCAL_PATH, bucket_name, DB_S3_KEY)
            print(f"Successfully uploaded flows.db to S3 bucket: {bucket_name}")
        except Exception as e:
            print(f"Error uploading to S3: {e}")

def save_to_dynamodb(table_name, company_name, final_audit):
    table = dynamodb.Table(table_name)
    try:
        # Convert string to dict if needed (DynamoDB prefers Maps/Dicts for JSON)
        if isinstance(final_audit, str):
            try:
                final_audit = json.loads(final_audit)
            except:
                pass

        item = {
            'id': str(uuid.uuid4()),
            'company_name': company_name or 'Unknown',
            'timestamp': datetime.utcnow().isoformat(),
            'audit_result': final_audit
        }
        table.put_item(Item=item)
        print(f"Successfully saved results to DynamoDB table: {table_name}")
    except Exception as e:
        print(f"Error saving to DynamoDB: {e}")

def lambda_handler(event, context):
    print("Received event:", event)

    # 1. Sync DB from S3 if bucket is configured
    s3_bucket_name = os.environ.get("S3_BUCKET_NAME")
    if s3_bucket_name:
        sync_db_from_s3(s3_bucket_name)

    # Optional: extract dynamic variables from the event (e.g., via API Gateway body)
    if isinstance(event.get('body'), str):
        try:
            body = json.loads(event['body'])
        except Exception:
            body = {}
    else:
        body = event

    company_name = body.get('company_name', None)
    pitch_deck = body.get('pitch_deck_content', None)
    email_body = body.get('email_body', None)

    flow = SafepitchFlow()
    flow.state['inputs'] = {}
    if company_name: flow.state['inputs']['company_name'] = company_name
    if pitch_deck: flow.state['inputs']['pitch_deck_content'] = pitch_deck
    if email_body: flow.state['inputs']['email_body'] = email_body

    # Execute the flow
    try:
        flow.kickoff()
    except Exception as e:
        print("Flow Execution Error:", e)
        # Sync DB back to S3 even if it fails, so we don't lose intermediate state
        if s3_bucket_name:
            sync_db_to_s3(s3_bucket_name)
        return {
            'statusCode': 500,
            'body': json.dumps({"error": str(e)})
        }

    # 2. Sync DB back to S3 on success
    if s3_bucket_name:
        sync_db_to_s3(s3_bucket_name)

    final_audit = flow.state.get('audit_report', "Flow completed but 'audit_report' not in state.")

    # 3. Save Final JSON Results to DynamoDB
    dynamodb_table_name = os.environ.get("DYNAMODB_TABLE_NAME")
    if dynamodb_table_name:
        save_to_dynamodb(dynamodb_table_name, company_name, final_audit)

    return {
        'statusCode': 200,
        'headers': { "Content-Type" : "application/json" },
        'body': json.dumps(final_audit)
    }