// src/components/ApplicationCard.jsx
import { ExternalLink, Settings, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useNavigate } from "react-router-dom"; // <-- yeni

const ApplicationCard = ({ application, onEdit, onDelete, onLaunch }) => {
  const navigate = useNavigate(); // <-- yeni

  const handleLaunch = () => {
    if (application.url) {
      if (application.url.startsWith("/")) {
        navigate(application.url); // iç rota: SPA yönlendirme
      } else {
        window.open(application.url, "_blank"); // dış link: yeni sekme
      }
    }
    if (onLaunch) onLaunch(application);
  };

  return (
    <Card className="group hover:shadow-lg transition-all duration-200 cursor-pointer">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            {application.icon_url ? (
              <img
                src={application.icon_url}
                alt={application.name}
                className="w-10 h-10 rounded-lg object-cover"
              />
            ) : (
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <ExternalLink className="h-5 w-5 text-blue-600" />
              </div>
            )}
            <div>
              <CardTitle className="text-lg">{application.name}</CardTitle>
              <CardDescription className="text-sm">
                {application.category || "Genel"}
              </CardDescription>
            </div>
          </div>

          <div className="flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
            {onEdit && (
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onEdit(application);
                }}
              >
                <Settings className="h-4 w-4" />
              </Button>
            )}
            {onDelete && (
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(application);
                }}
              >
                <Trash2 className="h-4 w-4 text-red-500" />
              </Button>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent onClick={handleLaunch}>
        <p className="text-sm text-gray-600 mb-4">
          {application.description || "Açıklama bulunmuyor"}
        </p>

        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500">
            {application.updated_at
              ? `Son güncelleme: ${new Date(
                  application.updated_at
                ).toLocaleDateString("tr-TR")}`
              : "Tarih bilgisi yok"}
          </span>

          <Button size="sm" className="group-hover:bg-blue-600">
            <ExternalLink className="h-4 w-4 mr-2" />
            Başlat
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default ApplicationCard;
