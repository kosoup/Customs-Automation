import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider } from "antd";
import koKR from "antd/locale/ko_KR";

import Dashboard from "./pages/Dashboard";
import DeclarationList from "./pages/DeclarationList";
import DeclarationEdit from "./pages/DeclarationEdit";
import InvoiceUpload from "./pages/InvoiceUpload";
import Settings from "./pages/Settings";

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={koKR}>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/declarations" element={<DeclarationList />} />
            <Route path="/invoices/upload" element={<InvoiceUpload />} />
            <Route path="/declarations/new" element={<DeclarationEdit />} />
            <Route path="/declarations/:id" element={<DeclarationEdit />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </ConfigProvider>
    </QueryClientProvider>
  );
}

export default App;
