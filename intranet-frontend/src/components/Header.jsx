import { Building2, User, Settings, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "../contexts/AuthContext";

const Header = () => {
  const { user, logout, isAdmin, canManageApplications } = useAuth();

  const handleLogout = async () => {
    try {
      if (window.confirm("Çıkış yapmak istediğinizden emin misiniz?")) {
        await logout();
      }
    } catch (error) {
      console.error("Logout error:", error);
    }
  };

  const handleSettings = () => {
    // TODO: Implement settings modal
    alert("Ayarlar sayfası yakında eklenecek");
  };

  const handleProfile = () => {
    // TODO: Implement profile modal
    alert("Profil sayfası yakında eklenecek");
  };

  const getRoleDisplayName = (role) => {
    switch (role) {
      case "admin":
        return "Yönetici";
      case "manager":
        return "Müdür";
      case "user":
        return "Kullanıcı";
      default:
        return "Kullanıcı";
    }
  };

  return (
    <header className="bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo ve Başlık */}
          <div className="flex items-center space-x-3">
            <Building2 className="h-8 w-8 text-blue-600" />
            <div>
              <h1 className="text-xl font-bold text-gray-900">
                Sigorta Intranet Sistemi
              </h1>
              <p className="text-sm text-gray-500">İntranet Sistemi</p>
            </div>
          </div>

          {/* Kullanıcı Menüsü */}
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <User className="h-5 w-5 text-gray-500" />
              <div className="text-right">
                <div className="text-sm font-medium text-gray-700">
                  {user?.first_name} {user?.last_name}
                </div>
                <div className="text-xs text-gray-500">
                  {getRoleDisplayName(user?.role)}
                  {user?.department && ` • ${user.department}`}
                </div>
              </div>
            </div>

            <Button
              variant="ghost"
              size="sm"
              onClick={handleProfile}
              title="Profil"
            >
              <User className="h-4 w-4" />
            </Button>

            {(isAdmin() || canManageApplications()) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleSettings}
                title="Ayarlar"
              >
                <Settings className="h-4 w-4" />
              </Button>
            )}

            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              title="Çıkış Yap"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
