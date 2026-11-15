import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import KdMeuFilme from "./pages/KdMeuFilme.tsx";

// Mesmas rotas usadas no site da Horizonte Digital (horizontedigital.org/kdmeufilme)
const App = () => (
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<Navigate to="/kdmeufilme" replace />} />
      <Route path="/kdmeufilme" element={<KdMeuFilme />} />
      <Route path="/kdmeufilme/titulo/:id" element={<KdMeuFilme />} />
      <Route path="/kdmeufilme/sobre" element={<KdMeuFilme />} />
      <Route path="*" element={<Navigate to="/kdmeufilme" replace />} />
    </Routes>
  </BrowserRouter>
);

export default App;
