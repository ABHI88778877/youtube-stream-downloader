let currentData = null;
let currentFilter = "all";

const $ = id => document.getElementById(id);
const form = $("extractForm");
const error = $("error");
const results = $("results");
const formatsEl = $("formats");
const videoEl = $("video");
const modal = $("modal");
const progressBar = $("progressBar");
const progressText = $("progressText");

form.addEventListener("submit", async e => {
  e.preventDefault();
  const url = $("url").value.trim();
  if (!url) return;

  setError("");
  $("extractBtn").disabled = true;
  $("extractBtn").textContent = "Extracting…";
  results.classList.add("hidden");
  videoEl.classList.add("hidden");

  try {
    const res = await fetch("/api/info", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({url})
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Extraction failed.");

    currentData = data;
    $("title").textContent = data.title || "YouTube video";
    $("meta").textContent =
      [data.channel, formatDuration(data.duration), `${data.formats.length} formats`]
      .filter(Boolean).join(" • ");

    if (data.thumbnail) {
      $("thumb").src = data.thumbnail;
      $("thumb").classList.remove("hidden");
    }

    videoEl.classList.remove("hidden");
    results.classList.remove("hidden");
    renderFormats();
  } catch (err) {
    setError(err.message);
  } finally {
    $("extractBtn").disabled = false;
    $("extractBtn").textContent = "Extract";
  }
});

document.querySelectorAll(".filter").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".filter").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    currentFilter = btn.dataset.kind;
    renderFormats();
  });
});

function renderFormats() {
  if (!currentData) return;

  let list = currentData.formats.filter(f =>
    currentFilter === "all" || f.kind === currentFilter
  );

  if (!list.length) {
    formatsEl.innerHTML = `<div class="muted">No formats in this category.</div>`;
    return;
  }

  formatsEl.innerHTML = list.map(f => {
    const size = f.filesize ? humanSize(f.filesize) : "Size unknown";
    const resolution = f.height ? `${f.height}p` : (f.resolution || "Audio");
    const fps = f.fps ? `${f.fps} FPS` : "";
    const codecs = [
      f.vcodec && f.vcodec !== "none" ? `V: ${f.vcodec}` : "",
      f.acodec && f.acodec !== "none" ? `A: ${f.acodec}` : ""
    ].filter(Boolean).join(" • ");

    return `
      <article class="card">
        <span class="badge">${labelFor(f.kind)}</span>
        <div class="resolution">${escapeHtml(resolution)}</div>
        <div class="formatName">${escapeHtml(f.format || `${f.ext || ""} • format ${f.id}`)}</div>
        <div class="details">
          ${escapeHtml([fps, codecs, size, f.dynamic_range].filter(Boolean).join(" • "))}
          <br>Format ID: ${escapeHtml(f.id)}
        </div>
        <div class="cardBottom">
          <button class="download" onclick='startDownload(${JSON.stringify(f.id)})'>Download</button>
        </div>
      </article>
    `;
  }).join("");
}

async function startDownload(formatId) {
  const button = event.currentTarget;
  button.disabled = true;
  button.textContent = "Starting…";

  try {
    const res = await fetch("/api/download", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({
        url: $("url").value.trim(),
        format_id: formatId,
        title: currentData.title
      })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Could not start download.");

    modal.classList.remove("hidden");
    $("modalTitle").textContent = `Downloading ${currentData.title}`;
    await pollJob(data.job_id);
  } catch (err) {
    setError(err.message);
  } finally {
    button.disabled = false;
    button.textContent = "Download";
  }
}

async function pollJob(jobId) {
  while (true) {
    const res = await fetch(`/api/jobs/${jobId}`);
    const data = await res.json();

    progressBar.style.width = `${data.percent || 0}%`;
    progressText.textContent =
      data.status === "finished" ? "Download complete." :
      data.status === "error" ? data.message :
      `${data.status || "working"} ${data.percent ? `• ${data.percent}%` : ""} ${data.speed || ""} ${data.eta ? `• ETA ${data.eta}` : ""}`;

    if (data.status === "finished") {
      if (data.download_url) {
        progressText.innerHTML = `Download complete. <a href="${data.download_url}">Save file</a>`;
      }
      return;
    }
    if (data.status === "error") return;

    await new Promise(r => setTimeout(r, 700));
  }
}

$("closeModal").onclick = () => modal.classList.add("hidden");
modal.addEventListener("click", e => {
  if (e.target === modal) modal.classList.add("hidden");
});

function labelFor(kind) {
  return kind === "video_audio" ? "VIDEO + AUDIO" :
         kind === "video" ? "VIDEO ONLY" :
         kind === "audio" ? "AUDIO ONLY" : "OTHER";
}
function formatDuration(s) {
  if (!s) return "";
  s = Number(s);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = Math.floor(s % 60);
  return h ? `${h}:${String(m).padStart(2,"0")}:${String(sec).padStart(2,"0")}` :
             `${m}:${String(sec).padStart(2,"0")}`;
}
function humanSize(n) {
  const units=["B","KB","MB","GB","TB"];
  let i=0, x=Number(n);
  while(x>=1024 && i<units.length-1){x/=1024;i++}
  return `${x.toFixed(i?1:0)} ${units[i]}`;
}
function setError(msg) {
  error.textContent = msg;
  error.classList.toggle("hidden", !msg);
}
function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
