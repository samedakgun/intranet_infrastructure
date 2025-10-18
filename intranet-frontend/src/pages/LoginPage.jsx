// src/pages/LoginPage.jsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    const res = await login({ username, password });
    setLoading(false);

    if (res.success) {
      // Rol fark etmeksizin anasayfaya yönlendir
      navigate("/", { replace: true });
    } else {
      setError(res.error || "Giriş başarısız");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="w-full max-w-md bg-white border rounded-xl p-6 shadow-sm">
        <h1 className="text-xl font-semibold mb-2">İntranet Girişi</h1>
        <p className="text-sm text-gray-600 mb-6">
          Lütfen kullanıcı bilgilerinizle giriş yapın.
        </p>

        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="block text-sm mb-1">Kullanıcı Adı</label>
            <input
              className="w-full border rounded-md px-3 py-2"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
            />
          </div>
          <div>
            <label className="block text-sm mb-1">Şifre</label>
            <input
              type="password"
              className="w-full border rounded-md px-3 py-2"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>

          {error && <div className="text-red-600 text-sm">{error}</div>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white rounded-md py-2 disabled:opacity-50"
          >
            {loading ? "Giriş yapılıyor..." : "Giriş yap"}
          </button>
        </form>
      </div>
    </div>
  );
}
