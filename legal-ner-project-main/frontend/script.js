const API_BASE =
  (location.hostname === "localhost" || location.hostname === "127.0.0.1")
    ? "http://localhost:8000"
    : `${location.protocol}//${location.hostname}:8000`;

const fileInput = document.getElementById("fileInput");
const uploadArea = document.getElementById("uploadArea");
const fileList = document.getElementById("fileList");
const processBtn = document.getElementById("processBtn");
const progressBar = document.getElementById("progressBar");
const progressFill = document.querySelector(".progress-fill");
const progressText = document.querySelector(".progress-text");
const resultsSection = document.getElementById("resultsSection");
const entityResults = document.getElementById("entityResults");
const documentAnalysis = document.getElementById("documentAnalysis");
const totalEntities = document.getElementById("totalEntities");
const uniqueEntities = document.getElementById("uniqueEntities");
const documentsProcessed = document.getElementById("documentsProcessed");
const entityFilter = document.getElementById("entityFilter");
const exportBtn = document.getElementById("exportBtn");
const mergedSummary = document.getElementById("mergedSummary");

let uploadedFile = null;
let extractedData = null;
let startTime = null;

// Drag & Drop Upload
uploadArea.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", handleFile);
uploadArea.addEventListener("dragover", (e) => {
  e.preventDefault();
  uploadArea.classList.add("dragover");
});
uploadArea.addEventListener("dragleave", () => {
  uploadArea.classList.remove("dragover");
});
uploadArea.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadArea.classList.remove("dragover");
  if (e.dataTransfer.files.length) {
    fileInput.files = e.dataTransfer.files;
    handleFile();
  }
});

function handleFile() {
  if (fileInput.files.length > 0) {
    uploadedFile = fileInput.files[0];
    renderFile(uploadedFile);
    processBtn.disabled = false;
  }
}

function renderFile(file) {
  fileList.innerHTML = `
    <div class="file-item">
      <div class="file-info">
        <span>📄</span>
        <div class="file-details">
          <h4>${file.name}</h4>
          <p>${(file.size / 1024).toFixed(2)} KB</p>
        </div>
      </div>
      <button class="remove-file">Remove</button>
    </div>
  `;
  document.querySelector(".remove-file").addEventListener("click", () => {
    uploadedFile = null;
    fileList.innerHTML = "";
    processBtn.disabled = true;
  });
}

// Handle Process
processBtn.addEventListener("click", async () => {
  if (!uploadedFile) return;

  const formData = new FormData();
  formData.append("file", uploadedFile);

  progressBar.style.display = "block";
  progressFill.style.width = "20%";
  progressText.textContent = "Uploading...";
  startTime = performance.now(); // ✅ start stopwatch

  try {
    const response = await fetch(`${API_BASE}/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      alert(`❌ Server error: ${response.status} ${response.statusText}\n${errorText}`);
      console.error("Server Error Details:", response.status, response.statusText, errorText);
      return;
    }

    progressFill.style.width = "60%";
    progressText.textContent = "Processing...";

    extractedData = await response.json();

    progressFill.style.width = "100%";
    progressText.textContent = "Done!";

    renderResults(extractedData);
  } catch (err) {
    alert("❌ Failed to connect to backend. Is FastAPI running?");
    console.error("Network/Fetch Error:", err);
  }
});

// Render Results
function renderResults(data) {
  resultsSection.style.display = "block";
  entityResults.innerHTML = "";
  documentAnalysis.innerHTML = "";
  mergedSummary.innerHTML = "";

  // ✅ Calculate elapsed time
  const endTime = performance.now();
  const elapsed = ((endTime - startTime) / 1000).toFixed(2);

  // Stats
  totalEntities.textContent = data.entities.length;
  uniqueEntities.textContent = new Set(data.entities.map(e => e.text)).size;
  documentsProcessed.textContent = 1;

  // Auto-populate filter options
  const uniqueLabels = [...new Set(data.entities.map(e => e.label))];
  entityFilter.innerHTML = `<option value="All">All Entities</option>`;
  uniqueLabels.forEach(label => {
    const opt = document.createElement("option");
    opt.value = label;
    opt.textContent = label;
    entityFilter.appendChild(opt);
  });

  // Build merged summary
  const summaryMap = {};
  data.entities.forEach(ent => {
    if (!summaryMap[ent.label]) summaryMap[ent.label] = {};
    summaryMap[ent.label][ent.text] = (summaryMap[ent.label][ent.text] || 0) + 1;
  });

  Object.entries(summaryMap).forEach(([label, items]) => {
    const div = document.createElement("div");
    div.innerHTML = `<h4>${label} (${Object.keys(items).length} unique)</h4>`;
    Object.entries(items).forEach(([text, count]) => {
      div.innerHTML += `<p>${text} (${count}x)</p>`;
    });
    mergedSummary.appendChild(div);
  });

  // Document Analysis
  const counts = {};
  data.entities.forEach(ent => {
    counts[ent.label] = (counts[ent.label] || 0) + 1;
  });
  documentAnalysis.innerHTML = `
    <p><b>${data.filename}</b></p>
    <p>${data.entities.length} entities found</p>
    <p>${Object.entries(counts).map(([k,v]) => `${k}: ${v}`).join(", ")}</p>
    <p>⚡ Processing time: ${elapsed}s</p>
  `;

  // Apply filter initially
  filterEntities("All");
}

// Filtering
entityFilter.addEventListener("change", () => {
  filterEntities(entityFilter.value);
});

function filterEntities(type) {
  if (!extractedData) return;

  entityResults.innerHTML = "";
  extractedData.entities.forEach(ent => {
    if (type === "All" || ent.label === type) {
      const div = document.createElement("div");
      div.className = "entity-item";
      div.innerHTML = `
        <span class="entity-type">${ent.label}</span>
        ${ent.text} 
        <span class="entity-confidence">(${(ent.score*100).toFixed(1)}%)</span>
        <p class="entity-source">Found in: ${extractedData.filename} (1 occurrences)</p>
      `;
      entityResults.appendChild(div);
    }
  });
}
