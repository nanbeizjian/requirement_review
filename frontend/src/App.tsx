import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { SessionProvider, useSession } from "./session/SessionContext";
import { SessionForm } from "./session/SessionForm";
import { AppShell } from "./shell/AppShell";
import { GlobalAlertsProvider } from "./shell/GlobalAlerts";
import { ProjectReviewListPage } from "./features/reviews/ProjectReviewListPage";
import { ReviewDetailPage } from "./features/review-detail/ReviewDetailPage";
import { ReportPage } from "./features/report/ReportPage";
import { ReviewsRefreshProvider } from "./features/reviews/ReviewsRefreshContext";

function SessionGate() {
  const { actor, setSession } = useSession();
  if (!actor) return <SessionForm onSubmit={setSession} />;
  return <Outlet />;
}

export default function App() {
  return (
    <SessionProvider>
      <GlobalAlertsProvider>
        <ReviewsRefreshProvider>
          <Routes>
            <Route element={<SessionGate />}>
              <Route element={<AppShell />}>
                <Route index element={<Navigate to="/reviews" replace />} />
                <Route path="/reviews" element={<ProjectReviewListPage />} />
                <Route path="/reviews/:reviewId" element={<ReviewDetailPage />} />
                <Route path="/reviews/:reviewId/report" element={<ReportPage />} />
                <Route path="*" element={<div>404</div>} />
              </Route>
            </Route>
          </Routes>
        </ReviewsRefreshProvider>
      </GlobalAlertsProvider>
    </SessionProvider>
  );
}
