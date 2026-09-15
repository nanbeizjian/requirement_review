import { useState } from "react";
import { useParams } from "react-router-dom";
import { useSession } from "../session/SessionContext";
import { useClient } from "../lib/useClient";
import ErrorBanner from "../components/ErrorBanner";
import { ApiError } from "../lib/errors";

export default function KnowledgeUploadPage() {
  const { projectId = "" } = useParams();
  const { session } = useSession();
  const client = useClient();
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<Error | null>(null);

  const canUpload = !!session && session.role === "admin" && session.projectId === projectId;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!session || !file) return;
    setError(null);
    try {
      const result = await client.uploadKnowledge(session, projectId, file);
      setStatus(`${result.filename} indexed as ${result.document_id}`);
    } catch (err) {
      setError(err as ApiError);
    }
  };

  return (
    <section aria-labelledby="knowledge-heading">
      <h1 id="knowledge-heading">Knowledge upload</h1>
      <p>Project: <code>{projectId}</code></p>
      <ErrorBanner error={error} />
      {!canUpload && (
        <p>You need an admin session matching this project id to upload knowledge.</p>
      )}
      {canUpload && (
        <form onSubmit={submit}>
          <label>
            Markdown file
            <input
              type="file"
              accept=".md,.markdown,text/markdown"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              required
            />
          </label>
          <button type="submit" disabled={!file}>Upload</button>
        </form>
      )}
      {status && <p role="status">{status}</p>}
    </section>
  );
}
