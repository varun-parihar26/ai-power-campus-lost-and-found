const API_BASE = "http://127.0.0.1:5000/api";
const SERVER_ORIGIN = "http://127.0.0.1:5000";

let currentFilter = "all";

const form = document.getElementById("item-form");
const imageInput = document.getElementById("image");
const preview = document.getElementById("preview");
const formStatus = document.getElementById("form-status");
const itemsGrid = document.getElementById("items-grid");
const matchesModal = document.getElementById("matches-modal");
const matchesGrid = document.getElementById("matches-grid");
const closeModalBtn = document.getElementById("close-modal");

// --- Image preview on select ---
imageInput.addEventListener("change", () => {
  const file = imageInput.files[0];
  if (file) {
    preview.src = URL.createObjectURL(file);
    preview.style.display = "block";
  }
});

// --- Search box ---
const searchInput = document.getElementById("search-input");
let searchDebounce;
searchInput.addEventListener("input", () => {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => {
    currentSearch = searchInput.value.trim();
    loadItems();
  }, 300);
});

// --- Filter buttons ---
document.querySelectorAll(".filter-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".filter-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    currentFilter = btn.dataset.filter;
    loadItems();
  });
});

// --- Submit new report ---
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  formStatus.textContent = "Uploading and analyzing image...";

  const formData = new FormData();
  formData.append("image", imageInput.files[0]);
  formData.append("title", document.getElementById("title").value);
  formData.append("description", document.getElementById("description").value);
  formData.append("category", document.getElementById("category").value);
  formData.append("location", document.getElementById("location").value);
  formData.append("contact_info", document.getElementById("contact_info").value);
  formData.append("status", document.querySelector('input[name="status"]:checked').value);

  try {
    const res = await fetch(`${API_BASE}/items`, { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || "Upload failed");
    }
    const created = await res.json();
    form.reset();
    preview.style.display = "none";
    loadItems();

    if (created.auto_matches && created.auto_matches.length > 0) {
      formStatus.textContent = `Report submitted! We found ${created.auto_matches.length} possible match(es) already.`;
      openMatchesView(created.auto_matches, created.id);
    } else {
      formStatus.textContent = "Report submitted! No strong matches yet — we'll keep checking new reports.";
    }
    setTimeout(() => (formStatus.textContent = ""), 4000);
  } catch (err) {
    formStatus.textContent = `Error: ${err.message}`;
  }
});

// --- Load & render items ---
let currentSearch = "";

async function loadItems() {
  let url;
  if (currentSearch) {
    url = `${API_BASE}/items/search?q=${encodeURIComponent(currentSearch)}`;
    if (currentFilter !== "all") url += `&status=${currentFilter}`;
  } else {
    url = currentFilter === "all" ? `${API_BASE}/items` : `${API_BASE}/items?status=${currentFilter}`;
  }
  const res = await fetch(url);
  const items = await res.json();

  itemsGrid.innerHTML = "";
  if (items.length === 0) {
    itemsGrid.innerHTML = `<div class="empty-state">No reports yet. Be the first to post one above.</div>`;
    return;
  }

  items.forEach((item) => {
    itemsGrid.appendChild(renderCard(item));
  });
}

function renderCard(item, similarity = null) {
  const card = document.createElement("div");
  card.className = "item-card";
  card.innerHTML = `
    <span class="tag ${item.status}">${item.status}</span>
    <div class="scan-line">
      <img src="${SERVER_ORIGIN}${item.image_url}" alt="${item.title}" />
    </div>
    <div class="item-body">
      ${similarity !== null ? `<span class="similarity-badge">${Math.round(similarity * 100)}% visual match</span>` : ""}
      <h3>${escapeHtml(item.title)}</h3>
      <p>${escapeHtml(item.location || "Location not specified")}</p>
      ${similarity === null ? `<button class="match-btn" data-id="${item.id}">Find Matches</button>` : ""}
    </div>
  `;
  if (similarity === null) {
    card.querySelector(".match-btn").addEventListener("click", () => showMatches(item.id));
  }
  return card;
}

// --- Matches modal ---
async function showMatches(itemId) {
  matchesModal.classList.remove("hidden");
  matchesGrid.innerHTML = `
    <div class="radar-scan">
      <div class="radar"><div class="radar-sweep"></div></div>
      <span class="radar-label">SCANNING FOR VISUAL MATCHES...</span>
    </div>
  `;

  const res = await fetch(`${API_BASE}/items/${itemId}/matches`);
  const matches = await res.json();
  openMatchesView(matches, itemId);
}

function openMatchesView(matches, sourceItemId) {
  matchesModal.classList.remove("hidden");
  matchesGrid.innerHTML = "";
  if (matches.length === 0) {
    matchesGrid.innerHTML = `<div class="empty-state">No strong matches found yet. Check back later.</div>`;
    return;
  }
  matches.forEach((m) => {
    const card = renderCard(m, m.similarity);
    const qrBtn = document.createElement("button");
    qrBtn.className = "match-btn";
    qrBtn.style.marginTop = "6px";
    qrBtn.textContent = "Get Claim QR";
    qrBtn.addEventListener("click", () => {
      window.open(`${API_BASE}/items/${sourceItemId}/claim-qr/${m.id}`, "_blank");
    });
    card.querySelector(".item-body").appendChild(qrBtn);
    matchesGrid.appendChild(card);
  });
}

closeModalBtn.addEventListener("click", () => matchesModal.classList.add("hidden"));
matchesModal.addEventListener("click", (e) => {
  if (e.target === matchesModal) matchesModal.classList.add("hidden");
});

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}

// Initial load
loadItems();
