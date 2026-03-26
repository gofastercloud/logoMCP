import { useEffect, useState } from "react";
import { checkHealth } from "./api/client";

function App() {
  const [backendStatus, setBackendStatus] = useState<string>("checking...");

  useEffect(() => {
    checkHealth()
      .then(() => setBackendStatus("connected"))
      .catch(() => setBackendStatus("offline"));
  }, []);

  return (
    <div style={{ padding: "2rem", fontFamily: "system-ui, sans-serif" }}>
      <h1>LogoGen</h1>
      <p>Local Brand Design System Generator</p>
      <p>
        Backend: <strong>{backendStatus}</strong>
      </p>
    </div>
  );
}

export default App;
