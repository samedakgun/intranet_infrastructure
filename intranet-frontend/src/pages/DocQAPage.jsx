// src/pages/DocQAPage.jsx
import { useEffect, useMemo, useState, useCallback, useRef } from "react";
import api from "../services/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function DocQAPage() {
  const fileInputRef = useRef(null);
  const openPicker = () => fileInputRef.current?.click();
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");

  const [dragOver, setDragOver] = useState(false);

  const [searchQ, setSearchQ] = useState("");
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState([]);

  const [selectedDoc, setSelectedDoc] = useState(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");

  const loadFiles = async () => {
    try {
      const data = await api.ragList();
      setFiles(data.docs || []);
    } catch (e) {
      console.error(e);
    }
  };
  useEffect(() => {
    loadFiles();
  }, []);

  const doUpload = async (fileList) => {
    if (!fileList?.length) return;
    setUploading(true);
    setError("");
    setUploadMsg("");
    try {
      let ok = 0,
        fail = 0;
      for (const f of fileList) {
        try {
          await api.ragUpload(f);
          ok++;
        } catch {
          fail++;
        }
      }
      setUploadMsg(`${ok} dosya yüklendi${fail ? `, ${fail} başarısız` : ""}.`);
      await loadFiles();
    } catch (e) {
      setError(e.message || "Yükleme hatası");
    } finally {
      setUploading(false);
    }
  };

  const onFileInputChange = async (e) => {
    const arr = Array.from(e.target.files || []);
    await doUpload(arr);
    e.target.value = "";
  };

  const onDrop = useCallback(async (e) => {
    e.preventDefault();
    setDragOver(false);
    const arr = Array.from(e.dataTransfer.files || []);
    await doUpload(arr);
  }, []);

  const onDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };
  const onDragLeave = () => setDragOver(false);

  const onSearch = async (e) => {
    e?.preventDefault?.();
    if (!searchQ.trim()) return;
    setSearching(true);
    setError("");
    setResults([]);
    try {
      const data = await api.ragSearch(searchQ, { k: 30, hybrid: true });
      const arr = data.results || [];
      // doc_id'ye göre grupla, en yüksek skorlu eşleşmeyi al
      const byDoc = {};
      for (const r of arr) {
        const did = r.doc_id;
        const score = Number(r.score || 0);
        if (!did) continue;
        if (!byDoc[did] || score > byDoc[did].score) {
          byDoc[did] = { doc_id: did, title: r.title, score };
        }
      }
      setResults(
        Object.values(byDoc)
          .sort((a, b) => b.score - a.score)
          .slice(0, 10)
      );
    } catch (e) {
      setError(e.message || "Arama hatası");
    } finally {
      setSearching(false);
    }
  };

  const onAsk = async (e) => {
    e?.preventDefault?.();
    if (!selectedDoc || !question.trim()) return;
    setAsking(true);
    setError("");
    setAnswer(null);
    try {
      const data = await api.ragAsk(selectedDoc.doc_id, question, { k: 6 });
      setAnswer(data);
    } catch (e) {
      setError(e.message || "Soru-cevap hatası");
    } finally {
      setAsking(false);
    }
  };

  const deleteDoc = async (docId) => {
    if (!confirm("Belgeyi silmek istiyor musunuz?")) return;
    try {
      await api.ragDelete(docId);
      await loadFiles();
      if (selectedDoc?.doc_id === docId) setSelectedDoc(null);
    } catch (e) {
      alert(e.message || "Silme hatası");
    }
  };

  const selectedTitle = useMemo(() => {
    if (!selectedDoc) return "";
    const f = files.find((x) => x.doc_id === selectedDoc.doc_id);
    return f?.title || selectedDoc.title || selectedDoc.doc_id;
  }, [selectedDoc, files]);

  return (
    <div className="space-y-6">
      {/* === BELGE YÜKLEME KARTI === */}
      <div
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        className={`rounded-2xl border-2 border-dashed p-6 bg-white transition
          ${dragOver ? "border-blue-500 bg-blue-50" : "border-gray-300"}`}
      >
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold">Belge Yükle</h2>
            <p className="text-sm text-gray-600">
              PDF, DOCX, TXT, MD dosyalarını sürükleyip bırakın veya butondan
              seçin.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <input
              ref={fileInputRef}
              id="file-input"
              type="file"
              multiple
              className="hidden"
              onChange={onFileInputChange}
              accept=".pdf,.docx,.txt,.md"
            />
            <Button type="button" onClick={openPicker} disabled={uploading}>
              {uploading ? "Yükleniyor..." : "Dosya Seç"}
            </Button>
          </div>
        </div>
        {uploadMsg && (
          <div className="text-sm text-green-700 mt-3">{uploadMsg}</div>
        )}
      </div>

      {/* === SOL: BELGELER & ARAMA | SAĞ: SORU-CEVAP === */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sol panel */}
        <div className="lg:col-span-1 space-y-4">
          <div className="border rounded-xl bg-white p-4">
            <h3 className="font-semibold mb-2">Belgeler</h3>
            <div className="max-h-80 overflow-auto divide-y">
              {files.length === 0 && (
                <div className="text-gray-500 text-sm py-3">
                  Henüz belge yok
                </div>
              )}
              {files.map((f) => (
                <div
                  key={f.doc_id}
                  className="py-2 flex items-start justify-between gap-2"
                >
                  <button
                    onClick={() =>
                      setSelectedDoc({ doc_id: f.doc_id, title: f.title })
                    }
                    className={`text-left flex-1 px-2 rounded hover:bg-gray-50 ${
                      selectedDoc?.doc_id === f.doc_id ? "bg-blue-50" : ""
                    }`}
                  >
                    <div className="text-sm font-medium">
                      {f.title || f.doc_id}
                    </div>
                    <div className="text-xs text-gray-500">{f.doc_id}</div>
                  </button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => deleteDoc(f.doc_id)}
                  >
                    Sil
                  </Button>
                </div>
              ))}
            </div>
          </div>

          <div className="border rounded-xl bg-white p-4">
            <h3 className="font-semibold mb-2">Arama</h3>
            <form onSubmit={onSearch} className="flex gap-2">
              <Input
                placeholder="Anahtar kelime..."
                value={searchQ}
                onChange={(e) => setSearchQ(e.target.value)}
              />
              <Button type="submit" disabled={searching || !searchQ.trim()}>
                {searching ? "Aranıyor..." : "Ara"}
              </Button>
            </form>
            <div className="mt-3 space-y-2">
              {results.map((r) => (
                <button
                  key={r.doc_id}
                  onClick={() => setSelectedDoc(r)}
                  className={`w-full text-left text-sm p-2 rounded border hover:bg-gray-50 ${
                    selectedDoc?.doc_id === r.doc_id
                      ? "border-blue-400"
                      : "border-gray-200"
                  }`}
                >
                  <div className="font-medium">{r.title || r.doc_id}</div>
                  <div className="text-xs text-gray-500">
                    score: {r.score?.toFixed?.(3)}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Sağ panel */}
        <div className="lg:col-span-2 space-y-4">
          <div className="border rounded-xl bg-white p-4">
            <h3 className="font-semibold mb-2">Soru-Cevap</h3>
            <div className="text-sm text-gray-600 mb-3">
              {selectedDoc ? (
                <>
                  Seçili belge: <b>{selectedTitle}</b>
                </>
              ) : (
                "Soldan bir belge seçin veya arama sonuçlarından birini tıklayın."
              )}
            </div>

            <form onSubmit={onAsk} className="flex gap-2">
              <Input
                placeholder="Sorunuzu yazın…"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                disabled={!selectedDoc}
              />
              <Button
                type="submit"
                disabled={!selectedDoc || !question.trim() || asking}
              >
                {asking ? "Yanıtlanıyor..." : "Sor"}
              </Button>
            </form>

            {error && (
              <div className="mt-3 text-red-600 text-sm">Hata: {error}</div>
            )}

            {answer?.answer && (
              <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded">
                <div className="text-sm text-gray-600 mb-1">Yanıt</div>
                <div className="whitespace-pre-wrap">{answer.answer}</div>
              </div>
            )}
            {answer?.chunks_used && (
              <div className="mt-3 text-xs text-gray-500">
                Kaynak parçalar: {answer.chunks_used.length}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
