import { Link, Outlet } from "react-router-dom";

function Layout() {
  return (
    <div className="layout">
      <header className="layout-header">
        <Link to="/" className="layout-logo">AI Research Copilot</Link>
        <nav className="layout-nav">
          <Link to="/sessions/new" className="layout-link">New Session</Link>
          <Link to="/sessions" className="layout-link">History</Link>
        </nav>
      </header>
      <main className="layout-main">
        <Outlet />
      </main>
    </div>
  );
}

export default Layout;
