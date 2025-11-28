const API_KEY = window.__ENV__.API_KEY;
const REGION = window.__ENV__.REGION;
const REST_API_ID = window.__ENV__.REST_API_ID;
const STAGE = window.__ENV__.STAGE;

const apigClient = apigClientFactory.newClient({
  apiKey: API_KEY,
});

async function renderResults(res) {
  const div = document.getElementById("results");
  div.innerHTML = "";
  for (const item of res) {
    const photoUrl = `https://${item.bucket}.s3.amazonaws.com/${item.objectKey}`;
    const img = document.createElement("img");
    img.src = photoUrl;
    img.className = "photo";
    div.appendChild(img);
  }
}

async function searchPhotos() {
  const query = document.getElementById("query").value;
  if (!query.trim()) {
    alert("Please enter a search query");
    return;
  }

  const params = { q: query };
  const additionalParams = { headers: {} };
  const body = {};

  try {
    const res = await apigClient.searchGet(params, body, additionalParams);
    const data = typeof res.data === "string" ? JSON.parse(res.data) : res.data;
    renderResults(data);
    if (data.length === 0) {
      alert("No photos found for your search");
    }
  } catch (err) {
    console.error("Search error:", err);
    alert("Error searching photos: " + err.message);
  }
}

async function uploadPhoto() {
  const file = document.getElementById("file").files[0];
  if (!file) {
    alert("Please select a file to upload.");
    return;
  }

  if (!file.type.startsWith("image/")) {
    alert("Please select an image file (jpg, jpeg, png, etc.)");
    return;
  }

  const labels = document.getElementById("labels").value || "";

  const params = {
    object: file.name,
    "Content-Type": file.type,
    "x-amz-meta-customLabels": labels,
  };

  const arrayBuffer = await file.arrayBuffer();
  const body = new Uint8Array(arrayBuffer);
  try {
    const res = await apigClient.photosObjectPut(params, body, {});
    console.log("Upload success:", res);
    alert("File uploaded successfully!");
  } catch (err) {
    console.error("Upload error:", err);
    alert("Error uploading file: " + err.message);
    return;
  }
}
