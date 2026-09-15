import { useId, useState, type FormEvent } from "react";
import { Button } from "../components/Button/Button";
import { FormField } from "../components/FormField/FormField";
import { Select } from "../components/Select/Select";
import type { Role } from "../api/types";
import type { Session } from "./storage";
import styles from "./SessionForm.module.css";

const ROLES: readonly Role[] = ["admin", "reviewer", "viewer"];

export function SessionForm({ onSubmit }: { onSubmit: (s: Session) => void }) {
  const userId = useId();
  const projectId = useId();
  const roleId = useId();
  const [u, setU] = useState("");
  const [p, setP] = useState("");
  const [r, setR] = useState<Role>("reviewer");

  function submit(e: FormEvent) {
    e.preventDefault();
    onSubmit({ userId: u.trim(), projectId: p.trim(), role: r });
  }

  const ready = u.trim().length > 0 && p.trim().length > 0;

  return (
    <form className={styles.form} onSubmit={submit}>
      <h1>建立会话</h1>
      <p className={styles.hint}>本地开发会话；不实现登录、用户管理或服务端身份。</p>
      <FormField id={userId} label="用户 ID" value={u} onChange={setU} required autoComplete="off" />
      <FormField id={projectId} label="项目 ID" value={p} onChange={setP} required autoComplete="off" />
      <Select id={roleId} label="角色" value={r} onChange={(v) => setR(v as Role)} options={ROLES.map((v) => ({ value: v, label: v }))} />
      <Button type="submit" disabled={!ready}>开始</Button>
    </form>
  );
}
