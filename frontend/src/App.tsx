import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Demo from "./pages/Demo";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/demo" element={<Demo />} />
        <Route path="*" element={<Navigate to="/demo" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
