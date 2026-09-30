import { Navigate, Route, Routes } from "react-router-dom";
import AppShell from "./components/layout/AppShell";
import JobLayout from "./components/layout/JobLayout";
import EdaPage from "./pages/EdaPage";
import ExportPage from "./pages/ExportPage";
import FeaturesPage from "./pages/FeaturesPage";
import OverviewPage from "./pages/OverviewPage";
import QualityPage from "./pages/QualityPage";
import UploadPage from "./pages/UploadPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<UploadPage />} />
        <Route path="/jobs/:jobId" element={<JobLayout />}>
          <Route index element={<Navigate to="overview" replace />} />
          <Route path="overview" element={<OverviewPage />} />
          <Route path="quality" element={<QualityPage />} />
          <Route path="eda" element={<EdaPage />} />
          <Route path="features" element={<FeaturesPage />} />
          <Route path="export" element={<ExportPage />} />
        </Route>
      </Route>
    </Routes>
  );
}