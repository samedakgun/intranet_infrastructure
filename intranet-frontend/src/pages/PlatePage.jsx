// src/pages/PlatePage.jsx
import { useState } from "react";
import api from "../services/api";

export default function PlatePage() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await api.detectPlate(file, {
        engine: "tesseract",
        includeCrops: false,
      });
      setResult(data);
    } catch (err) {
      setError(err?.message || "Bir hata oluştu");
    } finally {
      setLoading(false);
    }
  };

  const plateText = result?.detections?.[0]?.plate_text || "";

  return (
    <div className="max-w-3xl mx-auto py-8 px-4">
      <h2 className="text-2xl font-bold mb-2">Plaka Tanıma</h2>
      <p className="text-gray-600">Görsel yükleyin, plaka metnini alın.</p>

      <form onSubmit={onSubmit} className="mt-6 flex items-center gap-2">
        <input
          type="file"
          accept="image/*"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
        <button
          type="submit"
          disabled={!file || loading}
          className="px-4 py-2 bg-blue-600 text-white rounded-md disabled:opacity-50"
        >
          {loading ? "İşleniyor..." : "Gönder"}
        </button>
      </form>

      {error && <div className="mt-4 text-red-600">Hata: {error}</div>}

      {plateText && (
        <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded">
          <div className="font-semibold">Bulunan plaka:</div>
          <div className="text-2xl font-bold">{plateText}</div>
        </div>
      )}

      {result && (
        <pre className="mt-6 bg-gray-100 p-3 rounded overflow-auto text-sm">
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}
