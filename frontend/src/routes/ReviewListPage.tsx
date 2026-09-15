import { Link } from "react-router-dom";
import { useSession } from "../session/SessionContext";

export default function ReviewListPage() {
  const { session } = useSession();
  const canCreate = !!session && (session.role === "admin" || session.role === "reviewer");

  return (
    <section aria-labelledby="review-list-heading">
      <h1 id="review-list-heading">Reviews</h1>
      {!session && <p>Set a session to view reviews.</p>}
      {session && (
        <p>
          Use the backend <code>/api/v1/reviews</code> endpoint to enumerate review ids,
          or paste a review id into the URL.
        </p>
      )}
      {canCreate && (
        <p>
          <Link to="/reviews/new">Start a new review</Link>
        </p>
      )}
    </section>
  );
}
