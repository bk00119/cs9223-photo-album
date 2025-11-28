import json
import boto3
import os
import urllib.request
from botocore.awsrequest import AWSRequest
from botocore.auth import SigV4Auth

rekognition = boto3.client("rekognition")
s3 = boto3.client("s3")

OPENSEARCH_EP = os.environ["OPENSEARCH_EP"].rstrip("/")
INDEX = "photos"


def sigv4_open(
    url, method="PUT", body=None, headers=None, service="es", region=None, timeout=5
):
    if headers is None:
        headers = {}
    if body is not None and not isinstance(body, (bytes, bytearray)):
        body = body.encode("utf-8")
    if "Content-Type" not in headers:
        headers["Content-Type"] = "application/json"

    session = boto3.Session()
    creds = session.get_credentials().get_frozen_credentials()
    region = region or session.region_name or "us-east-1"

    awsReq = AWSRequest(method=method, url=url, data=body, headers=headers.copy())
    SigV4Auth(creds, service, region).add_auth(awsReq)

    signedHeaders = dict(awsReq.headers.items())

    req = urllib.request.Request(url, data=body, method=method, headers=signedHeaders)
    return urllib.request.urlopen(req, timeout=timeout)


def lambda_handler(event, context):
    r = event["Records"][0]
    bucket = r["s3"]["bucket"]["name"]
    key = r["s3"]["object"]["key"]

    res = rekognition.detect_labels(Image={"S3Object": {"Bucket": bucket, "Name": key}})
    labels = [label["Name"] for label in res["Labels"]]

    head = s3.head_object(Bucket=bucket, Key=key)
    meta = head.get("Metadata", {})
    customLabelsMeta = meta.get("customlabels", "")
    customLabels = [
        label.strip() for label in customLabelsMeta.split(",") if label.strip()
    ]

    doc = {
        "objectKey": key,
        "bucket": bucket,
        "createdTimestamp": head["LastModified"].isoformat(),
        "labels": [label.lower() for label in set(labels + customLabels)],
    }
    print("Document to index:", json.dumps(doc))

    url = f"{OPENSEARCH_EP}/{INDEX}/_doc/{key}"
    body = json.dumps(doc)
    res = sigv4_open(
        url=url,
        method="PUT",
        body=body,
        headers={"Content-Type": "application/json"},
    )

    print("OpenSearch response:", res.read().decode("utf-8"))
    return doc
