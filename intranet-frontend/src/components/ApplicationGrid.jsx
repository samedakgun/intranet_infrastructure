// src/components/ApplicationGrid.jsx
import { useState, useEffect } from "react";
import { Plus, Search, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import ApplicationCard from "./ApplicationCard";
import apiService from "../services/api";
import { useAuth } from "../contexts/AuthContext";
import { useNavigate } from "react-router-dom";

const ApplicationGrid = () => {
  const [applications, setApplications] = useState([]);
  const [filteredApplications, setFilteredApplications] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const { canManageApplications } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    loadApplications();
    loadCategories();
  }, []);

  const loadApplications = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getApplications();
      setApplications(data);
      setFilteredApplications(data);
    } catch (err) {
      setError(err.message);
      console.error("Failed to load applications:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadCategories = async () => {
    try {
      const data = await apiService.getCategories();
      setCategories(data);
    } catch (err) {
      console.error("Failed to load categories:", err);
    }
  };

  useEffect(() => {
    let filtered = applications;
    if (searchTerm) {
      filtered = filtered.filter(
        (app) =>
          app.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          app.description.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }
    if (selectedCategory !== "all") {
      filtered = filtered.filter((app) => app.category === selectedCategory);
    }
    setFilteredApplications(filtered);
  }, [applications, searchTerm, selectedCategory]);

  const handleAddApplication = () =>
    alert("Uygulama ekleme modalı yakında eklenecek");
  const handleEditApplication = (application) =>
    alert(`"${application.name}" düzenleme modalı yakında eklenecek`);
  const handleDeleteApplication = async (application) => {
    if (
      !window.confirm(
        `"${application.name}" uygulamasını silmek istiyor musunuz?`
      )
    )
      return;
    try {
      await apiService.deleteApplication(application.id);
      await loadApplications();
    } catch (err) {
      alert("Uygulama silinirken hata: " + err.message);
    }
  };
  const handleLaunchApplication = (application) =>
    console.log("Launching application:", application);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-500 mb-4">
          <p className="text-lg font-medium">Hata oluştu</p>
          <p className="text-sm">{error}</p>
        </div>
        <Button onClick={loadApplications}>Tekrar Dene</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Hızlı Erişim */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Plaka */}
        <div className="rounded-xl border bg-white p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="text-sm text-gray-500 font-medium">
              Hızlı Erişim
            </div>
            <h3 className="text-xl font-semibold mt-1">Plaka Tanımlama</h3>
            <p className="text-gray-600">
              Görsel yükleyin, plaka metnini anında alın.
            </p>
          </div>
          <Button
            onClick={() => navigate("/apps/plate")}
            className="w-full sm:w-auto"
          >
            Başlat
          </Button>
        </div>

        {/* Belge Soru-Cevap */}
        <div className="rounded-xl border bg-white p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="text-sm text-gray-500 font-medium">
              Hızlı Erişim
            </div>
            <h3 className="text-xl font-semibold mt-1">Belge Soru-Cevap</h3>
            <p className="text-gray-600">
              Belge yükle, ara ve seçili belgeye soru sor.
            </p>
          </div>
          <Button
            onClick={() => navigate("/apps/doc-qa")}
            className="w-full sm:w-auto"
          >
            Başlat
          </Button>
        </div>
      </div>

      {/* Başlık */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Uygulamalar</h2>
          <p className="text-gray-600">
            İntranet üzerindeki mevcut uygulamalar
          </p>
        </div>

        {canManageApplications() && (
          <Button
            onClick={handleAddApplication}
            className="flex items-center space-x-2"
          >
            <Plus className="h-4 w-4" />
            <span>Yeni Uygulama</span>
          </Button>
        )}
      </div>

      {/* Arama & Filtre */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Uygulama ara..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={selectedCategory} onValueChange={setSelectedCategory}>
          <SelectTrigger className="w-full sm:w-48">
            <Filter className="h-4 w-4 mr-2" />
            <SelectValue placeholder="Kategori seç" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tüm Kategoriler</SelectItem>
            {categories.map((category) => (
              <SelectItem key={category} value={category}>
                {category}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Grid */}
      {filteredApplications.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-gray-400 mb-4">
            <Plus className="h-12 w-12 mx-auto" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {searchTerm || selectedCategory !== "all"
              ? "Uygulama bulunamadı"
              : "Henüz uygulama yok"}
          </h3>
          <p className="text-gray-600 mb-4">
            {searchTerm || selectedCategory !== "all"
              ? "Arama kriterlerinizi değiştirmeyi deneyin"
              : "İlk uygulamanızı ekleyerek başlayın"}
          </p>
          {!searchTerm &&
            selectedCategory === "all" &&
            canManageApplications() && (
              <Button onClick={handleAddApplication}>
                <Plus className="h-4 w-4 mr-2" />
                Uygulama Ekle
              </Button>
            )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredApplications.map((application) => (
            <ApplicationCard
              key={application.id}
              application={application}
              onEdit={canManageApplications() ? handleEditApplication : null}
              onDelete={
                canManageApplications() ? handleDeleteApplication : null
              }
              onLaunch={handleLaunchApplication}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default ApplicationGrid;
