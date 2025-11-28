import json
import boto3
import os
import urllib.request
from botocore.awsrequest import AWSRequest
from botocore.auth import SigV4Auth


OPENSEARCH_EP = os.environ["OPENSEARCH_EP"].rstrip("/")
BOT_ID = os.environ["BOT_ID"]
BOT_ALIAS_ID = os.environ["BOT_ALIAS_ID"]
LOCALE_ID = "en_US"
AWS_REGION = "us-east-1"

lex = boto3.client("lexv2-runtime")


def sigv4_open(url, method="GET", body=None, region="us-east-1"):
    session = boto3.Session()
    creds = session.get_credentials().get_frozen_credentials()

    if body is not None and not isinstance(body, (bytes, bytearray)):
        body = body.encode("utf-8")
    headers = {"Content-Type": "application/json"}

    awsReq = AWSRequest(method=method, url=url, data=body, headers=headers)
    SigV4Auth(creds, "es", region).add_auth(awsReq)

    signedHeaders = dict(awsReq.headers.items())

    req = urllib.request.Request(url, data=body, method=method, headers=signedHeaders)
    return urllib.request.urlopen(req)


def lambda_handler(event, context):
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    }

    try:
        q = event.get("queryStringParameters", {}).get("q", "")
        print("Query:", q)

        if not q:
            return {"statusCode": 200, "headers": cors_headers, "body": json.dumps([])}

        lexRes = lex.recognize_text(
            botId=BOT_ID,
            botAliasId=BOT_ALIAS_ID,
            localeId=LOCALE_ID,
            sessionId="search-session",
            text=q,
        )
        print("Lex response:", json.dumps(lexRes))

        tokens = [t.strip().lower() for t in q.split() if t.strip()]
        print("Tokens:", tokens)
        if not tokens:
            return {"statusCode": 200, "headers": cors_headers, "body": json.dumps([])}

        opensearch_query = {"query": {"terms": {"labels.keyword": tokens}}}
        print("OpenSearch query:", json.dumps(opensearch_query))

        opensearch_url = f"{OPENSEARCH_EP}/photos/_search"
        res = sigv4_open(
            url=opensearch_url,
            method="GET",
            body=json.dumps(opensearch_query),
            region=AWS_REGION,
        )
        data = json.loads(res.read().decode("utf-8"))
        print("OpenSearch response:", json.dumps(data))

        hits = data.get("hits", {}).get("hits", [])
        photos = [hit["_source"] for hit in hits]
        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps(photos)}

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": cors_headers,
            "body": json.dumps({"error": str(e)}),
        }
