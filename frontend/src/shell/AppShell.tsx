import { Link, NavLink, Outlet } from "react-router-dom";
import { useSession } from "../session/SessionContext";
import styles from "./AppShell.module.css";

export function AppShell() {
  const { actor, reset } = useSession();
  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <h1 className={styles.brand}>Requirement Workbench</h1>
        <nav aria-label="主导航">
          <NavLink to="/reviews">评审列表</NavLink>
        </nav>
        <div className={styles.session}>
          {actor ? (
            <>
              <span>{actor.userId} · {actor.projectId} · {actor.role}</span>
              <button onClick={reset}>清除会话</button>
            </>
          ) : null}
        </div>
      </header>
      <main className={styles.main} id="main">
        <Outlet />
      </main>
      <footer className={styles.footer}>
        <Link to="/">关于</Link>
      </footer>
    </div>
  );
}
