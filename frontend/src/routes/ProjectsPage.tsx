import { useState } from "react";
import { useSession } from "../session/SessionContext";
import { useClient } from "../lib/useClient";
import ErrorBanner from "../components/ErrorBanner";
import { ApiError } from "../lib/errors";
import type { DataPolicy, Project } from "../api/types";

export default function ProjectsPage() {
  const { session } = useSession();
  const client = useClient();
  const [name, setName] = useState("");
  const [policy, setPolicy] = useState<DataPolicy>("local_only");
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState<Error | null>(null);

  const canCreate = !!session && session.role === "admin";

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!session) return;
    setError(null);
    try {
      const created = await client.createProject(session, { name, data_policy: policy });
      setProject(created);
      setName("");
    } catch (err) {
      setError(err as ApiError);
    }
  };

  return (
    <section aria-labelledby="projects-heading">
      <h1 id="projects-heading">Projects</h1>
      <ErrorBanner error={error} />
      {!session && <p>Set a session in the header to begin.</p>}
      {session && !canCreate && (
        <p>
          You are signed in as <code>{session.role}</code>. Only admins can create projects.
        </p>
      )}
      {canCreate && (
        <form onSubmit={submit} aria-label="Create project">
          <label>
            Name
            <input
              required
              maxLength={200}
              value={name}
              onChange={(e) => setName(e.target.value)}
              aria-required="true"
            />
          </label>
          <label>
            Data policy
            <select value={policy} onChange={(e) => setPolicy(e.target.value as DataPolicy)}>
              <option value="local_only">local_only</option>
              <option value="cloud_allowed">cloud_allowed</option>
              <option value="cloud_redacted">cloud_redacted</option>
            </select>
          </label>
          <button type="submit">Create</button>
        </form>
      )}
      {project && (
        <div className="card">
          <p>
            Created project <strong>{project.name}</strong> with id{" "}
            <code>{project.id}</code>.
          </p>
          <p>
            Use this id as <code>X-Project-ID</code> for subsequent calls.
          </p>
        </div>
      )}
    </section>
  );
}
