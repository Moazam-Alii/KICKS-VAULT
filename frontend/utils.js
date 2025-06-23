// Validate Solana wallet address (basic format check)
function isValidSolanaAddress(address) {
  return /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(address);
}

// Format long wallet for display (e.g., ABC...XYZ)
function formatWallet(address) {
  return address?.length > 10
    ? address.slice(0, 5) + '...' + address.slice(-4)
    : address;
}

// Save wallet to localStorage
function saveWallet(address) {
  if (isValidSolanaAddress(address)) {
    localStorage.setItem("user_wallet", address);
  }
}

// Get saved wallet from localStorage
function getWallet() {
  return localStorage.getItem("user_wallet");
}

// Clear saved wallet (for logout)
function clearWallet() {
  localStorage.removeItem("user_wallet");
}

// ✅ Validate uploaded image count (between 1 and 5)
function isValidImageCount(files) {
  return files && files.length >= 1 && files.length <= 5;
}

// Export for modules (optional, if using ES6 bundlers)
export {
  isValidSolanaAddress,
  formatWallet,
  saveWallet,
  getWallet,
  clearWallet,
  isValidImageCount
};
