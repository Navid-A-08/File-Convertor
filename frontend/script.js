const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const browseBtn = document.getElementById("browseBtn");
const fileInfo = document.getElementById("fileInfo");
const fileNameEl = document.getElementById("fileName");
const removeFileBtn = document.getElementById("removeFile");
const targetFormatEl = document.getElementById("targetFormat");
const optionsPanel = document.getElementById("optionsPanel");
const convertBtn = document.getElementById("convertBtn");
const statusEl = document.getElementById("status");

let selectedFile = null;
let capabilities = {};

async function loadCapabilities() {
  try {
    const res = await fetch("/api/formats");
    capabilities = await res.json();
  } catch {
    showStatus("Could not reach the conversion server.", "error");
  }
}
loadCapabilities();

function extOf(name) {
  return name.includes(".") ? name.split(".").pop().toLowerCase() : "";
}

function targetsForExt(ext) {
  const targets = new Set();
  Object.values(capabilities).forEach((sourceMap) => {
    if (sourceMap[ext]) sourceMap[ext].forEach((t) => targets.add(t));
  });
  return [...targets].sort();
}

function showStatus(message, kind) {
  statusEl.textContent = message;
  statusEl.className = `status status--${kind}`;
  statusEl.classList.remove("hidden");
}

function clearStatus() {
  statusEl.className = "status hidden";
  statusEl.textContent = "";
}

function setFile(file) {
  selectedFile = file;
  clearStatus();
  const ext = extOf(file.name);
  const targets = targetsForExt(ext);

  fileNameEl.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
  dropzone.classList.add("hidden");
  fileInfo.classList.remove("hidden");

  targetFormatEl.innerHTML = "";
  if (targets.length === 0) {
    targetFormatEl.innerHTML = `<option value="">No supported conversions for .${ext}</option>`;
    convertBtn.disabled = true;
  } else {
    targets.forEach((t) => {
      const opt = document.createElement("option");
      opt.value = t;
      opt.textContent = `.${t}`;
      targetFormatEl.appendChild(opt);
    });
    convertBtn.disabled = false;
  }
  renderOptions(targetFormatEl.value);
}

function renderOptions(targetExt) {
  optionsPanel.innerHTML = "";
  optionsPanel.classList.add("hidden");

  const imageExts = ["png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "ico"];
  const audioExts = ["mp3", "wav", "ogg", "flac", "m4a", "aac"];
  const fields = [];

  if (imageExts.includes(targetExt)) {
    fields.push({ name: "resize_width", label: "Resize width (px, optional)", type: "number" });
    fields.push({ name: "resize_height", label: "Resize height (px, optional)", type: "number" });
    if (["jpg", "jpeg", "webp"].includes(targetExt)) {
      fields.push({ name: "quality", label: "Quality (1-100)", type: "number", value: 90 });
    }
  }
  if (audioExts.includes(targetExt)) {
    fields.push({ name: "bitrate", label: "Bitrate", type: "text", value: "192k" });
  }

  if (fields.length === 0) return;
  optionsPanel.classList.remove("hidden");
  fields.forEach((f) => {
    const wrap = document.createElement("div");
    wrap.className = "form-row";
    wrap.innerHTML = `<label for="opt_${f.name}">${f.label}</label>
      <input type="${f.type}" id="opt_${f.name}" name="${f.name}" ${f.value !== undefined ? `value="${f.value}"` : ""}>`;
    optionsPanel.appendChild(wrap);
  });
}

targetFormatEl.addEventListener("change", () => renderOptions(targetFormatEl.value));

browseBtn.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", (e) => {
  if (e.target.files.length) setFile(e.target.files[0]);
});

["dragenter", "dragover"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  })
);
["dragleave", "drop"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
  })
);
dropzone.addEventListener("drop", (e) => {
  if (e.dataTransfer.files.length) setFile(e.dataTransfer.files[0]);
});

removeFileBtn.addEventListener("click", () => {
  selectedFile = null;
  fileInput.value = "";
  fileInfo.classList.add("hidden");
  dropzone.classList.remove("hidden");
  clearStatus();
});

convertBtn.addEventListener("click", async () => {
  if (!selectedFile || !targetFormatEl.value) return;

  const formData = new FormData();
  formData.append("file", selectedFile);
  formData.append("target_format", targetFormatEl.value);
  optionsPanel.querySelectorAll("input").forEach((input) => {
    if (input.value !== "") formData.append(input.name, input.value);
  });

  convertBtn.disabled = true;
  showStatus("Converting…", "busy");

  try {
    const res = await fetch("/api/convert", { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `Conversion failed (${res.status})`);
    }
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="?([^"]+)"?/);
    const filename = match ? match[1] : `converted.${targetFormatEl.value}`;

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);

    showStatus(`Done! Downloaded ${filename}`, "ok");
  } catch (err) {
    showStatus(err.message, "error");
  } finally {
    convertBtn.disabled = false;
  }
});
