import { Link, Route, Routes } from "react-router-dom";
import AppShell from "./components/AppShell";
import ProjectsPage from "./routes/ProjectsPage";
import KnowledgeUploadPage from "./routes/KnowledgeUploadPage";
import ReviewCreatePage from "./routes/ReviewCreatePage";
import ReviewListPage from "./routes/ReviewListPage";
import ReviewDetailPage from "./routes/ReviewDetailPage";
import FindingsPage from "./routes/FindingsPage";
import ApprovalPage from "./routes/ApprovalPage";
import ReportPage from "./routes/ReportPage";
import NotFoundPage from "./routes/NotFoundPage";

export default function App() {
  return (
    <AppShell
      nav={
        <nav aria-label="Primary">
          <Link to="/projects">Projects</Link>
          <Link to="/reviews">Reviews</Link>
        </nav>
      }
    >
      <Routes>
        <Route path="/" element={<ProjectsPage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/:projectId/knowledge" element={<KnowledgeUploadPage />} />
        <Route path="/reviews" element={<ReviewListPage />} />
        <Route path="/reviews/new" element={<ReviewCreatePage />} />
        <Route path="/reviews/:reviewId" element={<ReviewDetailPage />} />
        <Route path="/reviews/:reviewId/findings" element={<FindingsPage />} />
        <Route path="/reviews/:reviewId/approval" element={<ApprovalPage />} />
        <Route path="/reviews/:reviewId/report" element={<ReportPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AppShell>
  );
}
