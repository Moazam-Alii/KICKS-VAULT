const BACKEND_URL = "https://kicks-vault.onrender.com";

let walletAddress = null;

window.onload = async () => {
  setupUploadForm();
  await loadSneakers();
  await loadSneakerDetails();
};

async function loadSneakers() {
  const sneakerGrid = document.getElementById('sneakerGrid');
  if (!sneakerGrid) return;

  try {
    const sneakers = await fetch(`${BACKEND_URL}/sneakers`).then(res => res.json());
    if (!sneakers.length) {
      sneakerGrid.innerHTML = "<p>No sneakers listed yet.</p>";
      return;
    }

    sneakers.forEach(s => {
      const card = document.createElement("div");
      card.className = "card";
      const previewImg = s.image_urls?.[0] || "/static/default.jpg";
      card.innerHTML = `
  <a href="product.html?id=${s._id}">
    <img src="${s.image_url || s.image_urls?.[0] || '/static/placeholder.jpg'}" alt="${s.sku}">
  </a>
  <div class="card-body">
    <h4>${s.name || s.sku}</h4>
    <p><span class="label">Price:</span> <span class="value">${s.price || "N/A"} SOL</span></p>
    <p><span class="label">Owner:</span> <span class="value">${shortenWallet(s.owner)}</span></p>
  </div>
`;

      sneakerGrid.appendChild(card);
    });
  } catch (err) {
    sneakerGrid.innerHTML = "<p>Error loading sneakers.</p>";
  }
}

async function loadSneakerDetails() {
  const productSection = document.querySelector(".product-view");
  if (!productSection) return;

  const id = new URLSearchParams(window.location.search).get("id");
  if (!id) return;

  const sneaker = await fetch(`${BACKEND_URL}/sneaker/${id}`).then(res => res.json());

  const imageContainer = document.getElementById("sneakerImgContainer");
  imageContainer.innerHTML = "";

  if (Array.isArray(sneaker.image_urls)) {
    sneaker.image_urls.forEach(url => {
      const img = document.createElement("img");
      img.src = url;
      img.alt = sneaker.name;
      img.className = "product-img";
      imageContainer.appendChild(img);
    });
  } else {
    imageContainer.innerHTML = "<p>No images available.</p>";
  }

  document.getElementById("sneakerName").innerText = sneaker.name;
  document.getElementById("sku").innerText = sneaker.sku;
  document.getElementById("price").innerText = sneaker.price || "N/A";
  document.getElementById("owner").innerText = shortenWallet(sneaker.owner);

  const historyDiv = document.getElementById("mintHistory");
  historyDiv.innerHTML = "";

  if (Array.isArray(sneaker.mint_history)) {
    sneaker.mint_history.forEach((mint, i) => {
      const line = document.createElement("p");
      line.innerHTML = `<strong>Mint ${i + 1}:</strong> 
        <a href="https://explorer.solana.com/tx/${mint.mint_tx}?cluster=devnet" target="_blank">${mint.mint_tx}</a> 
        (by ${shortenWallet(mint.owner)}, ${new Date(mint.date).toLocaleString()})`;
      historyDiv.appendChild(line);
    });
  } else if (sneaker.mint_tx) {
    const line = document.createElement("p");
    line.innerHTML = `<strong>Mint:</strong> 
      <a href="https://explorer.solana.com/tx/${sneaker.mint_tx}?cluster=devnet" target="_blank">${sneaker.mint_tx}</a>`;
    historyDiv.appendChild(line);
  }

  document.getElementById("buyBtn").onclick = async () => {
    if (!window.solana || !window.solana.isPhantom) {
      alert("Phantom wallet not detected");
      return;
    }

    const wallet = await window.solana.connect();
    const buyer = wallet.publicKey.toString();

    const buyRes = await fetch(`${BACKEND_URL}/buy/${id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ buyer_wallet: buyer })
    });

    const result = await buyRes.json();
    document.getElementById("status").innerText = result.message || result.error;
    if (result.message) location.reload();
  };
}

function setupUploadForm() {
  const form = document.getElementById("uploadForm");
  if (!form) return;

  form.onsubmit = async (e) => {
    e.preventDefault();
    const formData = new FormData(form);
    const status = document.getElementById("status");
    status.innerText = "Verifying sneaker...";

    try {
      const res = await fetch(`${BACKEND_URL}/upload`, {
        method: "POST",
        body: formData
      });
      const result = await res.json();
      status.innerText = result.message || "Upload complete.";
      form.reset();
    } catch (err) {
      status.innerText = "Something went wrong during upload.";
    }
  };
}

function shortenWallet(addr) {
  return addr ? addr.slice(0, 4) + "..." + addr.slice(-4) : "N/A";
}

function isValidWallet(address) {
  return /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(address);
}
