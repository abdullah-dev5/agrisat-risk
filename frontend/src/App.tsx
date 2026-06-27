import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from './components/Layout';
import { DashboardPage } from './pages/DashboardPage';
import { FieldDetailPage } from './pages/FieldDetailPage';
import { FieldsListPage } from './pages/FieldsListPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterFieldPage } from './pages/RegisterFieldPage';
import { RegisterInstitutionPage } from './pages/RegisterInstitutionPage';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterInstitutionPage />} />
        <Route element={<AppLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/fields" element={<FieldsListPage />} />
          <Route path="/fields/new" element={<RegisterFieldPage />} />
          <Route path="/fields/:id" element={<FieldDetailPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
