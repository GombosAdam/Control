import { lazy, Suspense, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from './config/queryClient';
import { useAuthStore } from './stores/authStore';
import { AppLayout } from './components/layout/AppLayout';
import { LoginPage } from './features/auth/pages/LoginPage';

// Lazy loaded pages
const DashboardPage = lazy(() => import('./features/dashboard/pages/DashboardPage').then(m => ({ default: m.DashboardPage })));
const InvoiceListPage = lazy(() => import('./features/invoices/pages/InvoiceListPage').then(m => ({ default: m.InvoiceListPage })));
const InvoiceUploadPage = lazy(() => import('./features/invoices/pages/InvoiceUploadPage').then(m => ({ default: m.InvoiceUploadPage })));
const InvoiceProcessingPage = lazy(() => import('./features/invoices/pages/InvoiceProcessingPage').then(m => ({ default: m.InvoiceProcessingPage })));
const ExtractionQueuePage = lazy(() => import('./features/extraction/pages/ExtractionQueuePage').then(m => ({ default: m.ExtractionQueuePage })));
const ExtractionReviewPage = lazy(() => import('./features/extraction/pages/ExtractionReviewPage').then(m => ({ default: m.ExtractionReviewPage })));
const PartnersPage = lazy(() => import('./features/partners/pages/PartnersPage').then(m => ({ default: m.PartnersPage })));
const SuppliersPage = lazy(() => import('./features/partners/pages/SuppliersPage').then(m => ({ default: m.SuppliersPage })));
const CustomersPage = lazy(() => import('./features/partners/pages/CustomersPage').then(m => ({ default: m.CustomersPage })));
const ReportsPage = lazy(() => import('./features/reports/pages/ReportsPage').then(m => ({ default: m.ReportsPage })));
const MonthlyReportPage = lazy(() => import('./features/reports/pages/MonthlyReportPage').then(m => ({ default: m.MonthlyReportPage })));
const VatReportPage = lazy(() => import('./features/reports/pages/VatReportPage').then(m => ({ default: m.VatReportPage })));
const SupplierReportPage = lazy(() => import('./features/reports/pages/SupplierReportPage').then(m => ({ default: m.SupplierReportPage })));
const UsersPage = lazy(() => import('./features/admin/pages/UsersPage').then(m => ({ default: m.UsersPage })));
const SettingsPage = lazy(() => import('./features/admin/pages/SettingsPage').then(m => ({ default: m.SettingsPage })));
const SystemPage = lazy(() => import('./features/admin/pages/SystemPage').then(m => ({ default: m.SystemPage })));
const AuditPage = lazy(() => import('./features/admin/pages/AuditPage').then(m => ({ default: m.AuditPage })));

function PageLoading() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '256px' }}>
      <div style={{
        width: '32px', height: '32px', border: '3px solid #e5e7eb',
        borderTopColor: '#3B82F6', borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
      }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function AuthenticatedApp() {
  return (
    <BrowserRouter>
      <Suspense fallback={<PageLoading />}>
        <Routes>
          <Route path="/" element={<AppLayout />}>
            <Route index element={null} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="invoices" element={<InvoiceListPage />} />
            <Route path="invoices/upload" element={<InvoiceUploadPage />} />
            <Route path="invoices/processing" element={<InvoiceProcessingPage />} />
            <Route path="extraction/queue" element={<ExtractionQueuePage />} />
            <Route path="extraction/review" element={<ExtractionReviewPage />} />
            <Route path="partners" element={<PartnersPage />} />
            <Route path="partners/suppliers" element={<SuppliersPage />} />
            <Route path="partners/customers" element={<CustomersPage />} />
            <Route path="reports" element={<ReportsPage />} />
            <Route path="reports/monthly" element={<MonthlyReportPage />} />
            <Route path="reports/vat" element={<VatReportPage />} />
            <Route path="reports/suppliers" element={<SupplierReportPage />} />
            <Route path="admin/users" element={<UsersPage />} />
            <Route path="admin/settings" element={<SettingsPage />} />
            <Route path="admin/system" element={<SystemPage />} />
            <Route path="admin/audit" element={<AuditPage />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

function App() {
  const { isAuthenticated, isLoading, restoreSession } = useAuthStore();

  useEffect(() => { restoreSession(); }, []);

  if (isLoading) return <PageLoading />;
  if (!isAuthenticated) return <LoginPage />;

  return (
    <QueryClientProvider client={queryClient}>
      <AuthenticatedApp />
    </QueryClientProvider>
  );
}

export default App;
