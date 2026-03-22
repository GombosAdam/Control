import { lazy, Suspense, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from './config/queryClient';
import { useAuthStore } from './stores/authStore';
import { AppLayout } from './components/layout/AppLayout';
import { LoginPage } from './features/auth/pages/LoginPage';
import { RoleGuard } from './components/auth/RoleGuard';

// Lazy loaded pages
const DashboardPage = lazy(() => import('./features/dashboard/pages/DashboardPage').then(m => ({ default: m.DashboardPage })));
const InvoiceListPage = lazy(() => import('./features/invoices/pages/InvoiceListPage').then(m => ({ default: m.InvoiceListPage })));
const InvoiceUploadPage = lazy(() => import('./features/invoices/pages/InvoiceUploadPage').then(m => ({ default: m.InvoiceUploadPage })));
const InvoiceProcessingPage = lazy(() => import('./features/invoices/pages/InvoiceProcessingPage').then(m => ({ default: m.InvoiceProcessingPage })));
const ApprovalQueuePage = lazy(() => import('./features/invoices/pages/ApprovalQueuePage').then(m => ({ default: m.ApprovalQueuePage })));
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
const AccountingPage = lazy(() => import('./features/accounting/pages/AccountingPage').then(m => ({ default: m.AccountingPage })));
const GpuControlPage = lazy(() => import('./features/admin/pages/GpuControlPage').then(m => ({ default: m.GpuControlPage })));
const AccountingTemplatesPage = lazy(() => import('./features/accounting/pages/AccountingTemplatesPage').then(m => ({ default: m.AccountingTemplatesPage })));

// New controlling pages
const BudgetPage = lazy(() => import('./features/budget/pages/BudgetPage').then(m => ({ default: m.BudgetPage })));
const BudgetPlanningPage = lazy(() => import('./features/budget/pages/BudgetPlanningPage').then(m => ({ default: m.BudgetPlanningPage })));
const OrdersPage = lazy(() => import('./features/orders/pages/OrdersPage').then(m => ({ default: m.OrdersPage })));
const NewOrderPage = lazy(() => import('./features/orders/pages/NewOrderPage').then(m => ({ default: m.NewOrderPage })));
const ReconciliationPage = lazy(() => import('./features/reconciliation/pages/ReconciliationPage').then(m => ({ default: m.ReconciliationPage })));
const AccountingEntriesPage = lazy(() => import('./features/accounting/pages/AccountingEntriesPage').then(m => ({ default: m.AccountingEntriesPage })));
const ControllingPage = lazy(() => import('./features/controlling/pages/ControllingPage').then(m => ({ default: m.ControllingPage })));
const PlanActualPage = lazy(() => import('./features/controlling/pages/PlanActualPage').then(m => ({ default: m.PlanActualPage })));
const EbitdaPage = lazy(() => import('./features/controlling/pages/EbitdaPage').then(m => ({ default: m.EbitdaPage })));
const CommitmentPage = lazy(() => import('./features/controlling/pages/CommitmentPage').then(m => ({ default: m.CommitmentPage })));
const ChatPage = lazy(() => import('./features/chat/pages/ChatPage').then(m => ({ default: m.ChatPage })));

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
            <Route path="invoices/approvals" element={<ApprovalQueuePage />} />
            <Route path="extraction/queue" element={<RoleGuard roles={['admin', 'accountant']}><ExtractionQueuePage /></RoleGuard>} />
            <Route path="extraction/review" element={<RoleGuard roles={['admin', 'accountant']}><ExtractionReviewPage /></RoleGuard>} />
            <Route path="budget" element={<RoleGuard roles={['admin', 'cfo', 'department_head', 'accountant']}><BudgetPage /></RoleGuard>} />
            <Route path="budget/planning" element={<RoleGuard roles={['admin', 'cfo', 'department_head', 'accountant']}><BudgetPlanningPage /></RoleGuard>} />
            <Route path="orders" element={<RoleGuard roles={['admin', 'cfo', 'department_head', 'accountant']}><OrdersPage /></RoleGuard>} />
            <Route path="orders/new" element={<RoleGuard roles={['admin', 'cfo', 'department_head', 'accountant']}><NewOrderPage /></RoleGuard>} />
            <Route path="reconciliation" element={<RoleGuard roles={['admin', 'cfo', 'accountant']}><ReconciliationPage /></RoleGuard>} />
            <Route path="accounting" element={<RoleGuard roles={['admin', 'cfo', 'accountant']}><AccountingPage /></RoleGuard>} />
            <Route path="accounting/entries" element={<RoleGuard roles={['admin', 'cfo', 'accountant']}><AccountingEntriesPage /></RoleGuard>} />
            <Route path="accounting/templates" element={<RoleGuard roles={['admin', 'accountant']}><AccountingTemplatesPage /></RoleGuard>} />
            <Route path="controlling" element={<RoleGuard roles={['admin', 'cfo', 'department_head']}><ControllingPage /></RoleGuard>} />
            <Route path="controlling/ebitda" element={<RoleGuard roles={['admin', 'cfo', 'department_head']}><EbitdaPage /></RoleGuard>} />
            <Route path="controlling/commitment" element={<RoleGuard roles={['admin', 'cfo', 'department_head']}><CommitmentPage /></RoleGuard>} />
            <Route path="partners" element={<RoleGuard roles={['admin', 'accountant']}><PartnersPage /></RoleGuard>} />
            <Route path="partners/suppliers" element={<RoleGuard roles={['admin', 'accountant']}><SuppliersPage /></RoleGuard>} />
            <Route path="partners/customers" element={<RoleGuard roles={['admin', 'accountant']}><CustomersPage /></RoleGuard>} />
            <Route path="reports" element={<RoleGuard roles={['admin', 'cfo', 'department_head']}><ReportsPage /></RoleGuard>} />
            <Route path="reports/monthly" element={<RoleGuard roles={['admin', 'cfo', 'department_head']}><MonthlyReportPage /></RoleGuard>} />
            <Route path="reports/vat" element={<RoleGuard roles={['admin', 'cfo', 'department_head']}><VatReportPage /></RoleGuard>} />
            <Route path="reports/suppliers" element={<RoleGuard roles={['admin', 'cfo', 'department_head']}><SupplierReportPage /></RoleGuard>} />
            <Route path="admin/users" element={<RoleGuard roles={['admin']}><UsersPage /></RoleGuard>} />
            <Route path="admin/settings" element={<RoleGuard roles={['admin']}><SettingsPage /></RoleGuard>} />
            <Route path="admin/system" element={<RoleGuard roles={['admin']}><SystemPage /></RoleGuard>} />
            <Route path="admin/audit" element={<RoleGuard roles={['admin']}><AuditPage /></RoleGuard>} />
            <Route path="admin/gpu" element={<RoleGuard roles={['admin']}><GpuControlPage /></RoleGuard>} />
            <Route path="chat" element={<ChatPage />} />
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
