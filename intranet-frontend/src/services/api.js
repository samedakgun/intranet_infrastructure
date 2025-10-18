// src/services/api.js
const API_HOST = import.meta.env.VITE_API_BASE_URL || "http://localhost:5001";
const API_BASE_URL = `${API_HOST}/api`;

class ApiService {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;

    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    };

    const config = {
      credentials: "include",
      ...options,
      headers,
    };

    // Body nesneyse JSON'a çevir (FormData hariç)
    if (
      config.body &&
      typeof config.body === "object" &&
      !(config.body instanceof FormData)
    ) {
      config.body = JSON.stringify(config.body);
    }
    // FormData gönderiyorsak Content-Type'i tarayıcı ayarlasın
    if (config.body instanceof FormData) {
      delete config.headers["Content-Type"];
    }

    const res = await fetch(url, config);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP error! status: ${res.status}`);
    }
    if (res.status === 204) return null;
    return res.json();
  }

  // ---------- Auth ----------
  async login(credentials) {
    return this.request("/auth/login", { method: "POST", body: credentials });
  }
  async logout() {
    return this.request("/auth/logout", { method: "POST" });
  }
  async register(userData) {
    return this.request("/auth/register", { method: "POST", body: userData });
  }
  async getCurrentUser() {
    return this.request("/auth/me");
  }
  async checkSession() {
    return this.request("/auth/check-session");
  }
  async changePassword(data) {
    return this.request("/auth/change-password", {
      method: "POST",
      body: data,
    });
  }

  // ---------- Applications ----------
  async getApplications() {
    return this.request("/applications");
  }
  async getApplication(id) {
    return this.request(`/applications/${id}`);
  }
  async createApplication(d) {
    return this.request("/applications", { method: "POST", body: d });
  }
  async updateApplication(id, d) {
    return this.request(`/applications/${id}`, { method: "PUT", body: d });
  }
  async deleteApplication(id) {
    return this.request(`/applications/${id}`, { method: "DELETE" });
  }
  async getCategories() {
    return this.request("/applications/categories");
  }

  // ---------- Users ----------
  async getUsers() {
    return this.request("/users");
  }
  async getUser(id) {
    return this.request(`/users/${id}`);
  }
  async createUser(d) {
    return this.request("/users", { method: "POST", body: d });
  }
  async updateUser(id, d) {
    return this.request(`/users/${id}`, { method: "PUT", body: d });
  }
  async deleteUser(id) {
    return this.request(`/users/${id}`, { method: "DELETE" });
  }

  // ---------- Plate Detection ----------
  async detectPlate(file, { engine = "tesseract", includeCrops = false } = {}) {
    const form = new FormData();
    form.append("image", file);
    const qs = `?ocr_engine=${engine}&include_crops=${includeCrops}`;
    return this.request(`/plate/detect${qs}`, { method: "POST", body: form });
  }

  // ---------- RAG: Belge Soru-Cevap ----------
  async ragUpload(file) {
    const form = new FormData();
    form.append("file", file);
    return this.request("/rag/files", { method: "POST", body: form });
  }

  async ragList() {
    return this.request("/rag/files");
  }

  async ragDelete(docId) {
    return this.request(`/rag/files/${docId}`, { method: "DELETE" });
  }

  async ragSearch(q, { k = 20, hybrid = true, docId = null } = {}) {
    const params = new URLSearchParams({
      q,
      k: String(k),
      hybrid: String(hybrid),
    });
    if (docId) params.set("doc_id", docId); // backend destekliyorsa filtreler; değilse yok sayılır
    return this.request(`/rag/search?${params.toString()}`);
  }

  async ragAsk(docId, question, { k = 6 } = {}) {
    return this.request("/rag/ask", {
      method: "POST",
      body: { doc_id: docId, question, k },
    });
  }
}

export default new ApiService();
