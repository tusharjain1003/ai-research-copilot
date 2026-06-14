import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import SessionCreate from "./pages/SessionCreate";
import SessionHistory from "./pages/SessionHistory";
import SessionDetail from "./pages/SessionDetail";

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/sessions" replace />} />
        <Route path="/sessions" element={<SessionHistory />} />
        <Route path="/sessions/new" element={<SessionCreate />} />
        <Route path="/sessions/:id" element={<SessionDetail />} />
      </Route>
    </Routes>
  );
}

export default App;
