import {
  LayoutDashboard,
  FileText,
  ScanSearch,
  Building2,
  BarChart3,
  Settings,
  Upload,
  Loader,
  ListChecks,
  Eye,
  Truck,
  Users as UsersIcon,
  Sliders,
  Monitor,
  ClipboardList,
  ClipboardCheck,
  TrendingUp,
  Receipt,
  BookOpen,
  Cpu,
  Wallet,
  ShoppingCart,
  GitCompareArrows,
  Target,
  Plus,
  MessageCircle,
  Landmark,
  RefreshCw,
  Send,
  GitBranch,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { UserRole } from '../types/user';

export interface ModuleItem {
  icon: LucideIcon;
  path: string;
  labelKey: string;
}

export interface ModuleDefinition {
  nameKey: string;
  color: string;
  icon: LucideIcon;
  routes: string[];
  items: ModuleItem[];
  roles?: UserRole[];
  /** Permission resource — if set, module is visible when user has any permission on this resource */
  permission?: string;
  /** Which service panel this module belongs to */
  service: 'ai' | 'pipeline' | 'finance' | 'nav';
}

export const modules: Record<string, ModuleDefinition> = {
  // ── AI & Analytics (ai-service) ──
  chat: {
    nameKey: 'modules.chat',
    color: '#8B5CF6',
    icon: MessageCircle,
    routes: ['/chat'],
    service: 'ai',
    roles: ['admin', 'cfo', 'department_head', 'accountant', 'reviewer', 'clerk'],
    items: [
      { icon: MessageCircle, path: '/chat', labelKey: 'nav.chat' },
    ],
  },
  gpu: {
    nameKey: 'modules.gpu',
    color: '#22C55E',
    icon: Cpu,
    routes: ['/admin/gpu'],
    service: 'pipeline',
    roles: ['admin'],
    items: [
      { icon: Cpu, path: '/admin/gpu', labelKey: 'nav.gpu' },
    ],
  },
  admin: {
    nameKey: 'modules.admin',
    color: '#6B7280',
    icon: Settings,
    routes: ['/admin'],
    service: 'ai',
    roles: ['admin'],
    permission: 'admin',
    items: [
      { icon: UsersIcon, path: '/admin/users', labelKey: 'nav.users' },
      { icon: Sliders, path: '/admin/settings', labelKey: 'nav.settings' },
      { icon: Monitor, path: '/admin/system', labelKey: 'nav.system' },
      { icon: ClipboardList, path: '/admin/audit', labelKey: 'nav.audit' },
      { icon: Building2, path: '/admin/departments', labelKey: 'nav.departments' },
      { icon: GitBranch, path: '/admin/positions', labelKey: 'nav.positions' },
      { icon: ClipboardCheck, path: '/admin/po-approvals', labelKey: 'nav.poApprovals' },
      { icon: Settings, path: '/admin/permissions', labelKey: 'nav.permissions' },
    ],
  },

  // ── Számlák & Pipeline (invoice-pipeline) ──
  invoices: {
    nameKey: 'modules.invoices',
    color: '#10B981',
    icon: FileText,
    routes: ['/invoices', '/dashboard'],
    service: 'pipeline',
    roles: ['admin', 'cfo', 'department_head', 'accountant', 'reviewer', 'clerk'],
    permission: 'invoices',
    items: [
      { icon: LayoutDashboard, path: '/dashboard', labelKey: 'nav.dashboard' },
      { icon: FileText, path: '/invoices', labelKey: 'nav.invoices' },
      { icon: Upload, path: '/invoices/upload', labelKey: 'nav.upload' },
      { icon: Loader, path: '/invoices/processing', labelKey: 'nav.processing' },
      { icon: ClipboardCheck, path: '/invoices/approvals', labelKey: 'nav.approvals' },
    ],
  },
  extraction: {
    nameKey: 'modules.extraction',
    color: '#0EA5E9',
    icon: ScanSearch,
    routes: ['/extraction'],
    service: 'pipeline',
    roles: ['admin', 'accountant'],
    permission: 'invoices.extraction',
    items: [
      { icon: ListChecks, path: '/extraction/queue', labelKey: 'nav.extractionQueue' },
      { icon: Eye, path: '/extraction/review', labelKey: 'nav.extractionReview' },
    ],
  },
  reconciliation: {
    nameKey: 'modules.reconciliation',
    color: '#0d9488',
    icon: GitCompareArrows,
    routes: ['/reconciliation'],
    service: 'pipeline',
    roles: ['admin', 'cfo', 'accountant'],
    permission: 'reconciliation',
    items: [
      { icon: GitCompareArrows, path: '/reconciliation', labelKey: 'nav.reconciliation' },
    ],
  },
  partners: {
    nameKey: 'modules.partners',
    color: '#F59E0B',
    icon: Building2,
    routes: ['/partners'],
    service: 'pipeline',
    roles: ['admin', 'accountant'],
    permission: 'partners',
    items: [
      { icon: Building2, path: '/partners', labelKey: 'nav.partners' },
      { icon: Truck, path: '/partners/suppliers', labelKey: 'nav.suppliers' },
      { icon: UsersIcon, path: '/partners/customers', labelKey: 'nav.customers' },
    ],
  },

  // ── Pénzügy (finance-service) ──
  budget: {
    nameKey: 'modules.budget',
    color: '#8B5CF6',
    icon: Wallet,
    routes: ['/budget'],
    service: 'finance',
    roles: ['admin', 'cfo', 'department_head', 'accountant'],
    permission: 'budget',
    items: [
      { icon: Wallet, path: '/budget', labelKey: 'nav.budget' },
      { icon: TrendingUp, path: '/budget/planning', labelKey: 'nav.budgetPlanning' },
    ],
  },
  orders: {
    nameKey: 'modules.orders',
    color: '#06B6D4',
    icon: ShoppingCart,
    routes: ['/orders'],
    service: 'finance',
    roles: ['admin', 'cfo', 'department_head', 'accountant', 'clerk'],
    permission: 'orders',
    items: [
      { icon: ShoppingCart, path: '/orders', labelKey: 'nav.orders' },
      { icon: Plus, path: '/orders/new', labelKey: 'nav.newOrder' },
    ],
  },
  accounting: {
    nameKey: 'modules.accounting',
    color: '#0EA5E9',
    icon: BookOpen,
    routes: ['/accounting'],
    service: 'pipeline',
    roles: ['admin', 'cfo', 'accountant'],
    permission: 'accounting',
    items: [
      { icon: BookOpen, path: '/accounting', labelKey: 'nav.accounting' },
      { icon: ListChecks, path: '/accounting/entries', labelKey: 'nav.entries' },
      { icon: Receipt, path: '/accounting/templates', labelKey: 'nav.accountingTemplates' },
    ],
  },
  controlling: {
    nameKey: 'modules.controlling',
    color: '#EF4444',
    icon: Target,
    routes: ['/controlling'],
    service: 'finance',
    roles: ['admin', 'cfo', 'department_head'],
    permission: 'controlling',
    items: [
      { icon: Target, path: '/controlling/ebitda', labelKey: 'nav.planning' },
      { icon: GitCompareArrows, path: '/controlling/commitment', labelKey: 'nav.commitment' },
    ],
  },
  reports: {
    nameKey: 'modules.reports',
    color: '#1e3a5f',
    icon: BarChart3,
    routes: ['/reports'],
    service: 'finance',
    roles: ['admin', 'cfo', 'department_head'],
    permission: 'reports',
    items: [
      { icon: BarChart3, path: '/reports', labelKey: 'nav.reports' },
      { icon: TrendingUp, path: '/reports/monthly', labelKey: 'nav.monthly' },
      { icon: Receipt, path: '/reports/vat', labelKey: 'nav.vat' },
      { icon: Truck, path: '/reports/suppliers', labelKey: 'nav.supplierReport' },
    ],
  },

  // ── NAV Online Számla ──
  navOnlineSzamla: {
    nameKey: 'modules.navOnlineSzamla',
    color: '#DC2626',
    icon: Landmark,
    routes: ['/nav'],
    service: 'nav',
    roles: ['admin', 'accountant'],
    permission: 'nav',
    items: [
      { icon: Settings, path: '/nav/settings', labelKey: 'nav.navSettings' },
      { icon: RefreshCw, path: '/nav/sync', labelKey: 'nav.navSync' },
      { icon: Send, path: '/nav/submissions', labelKey: 'nav.navSubmissions' },
    ],
  },
};

export type ModuleKey = keyof typeof modules;

/** Service panel definitions for the launcher */
export const servicePanels = [
  {
    key: 'pipeline' as const,
    labelKey: 'launcher.pipeline',
    color: '#10B981',
    description: 'launcher.pipelineDesc',
    defaultOpen: true,
  },
  {
    key: 'ai' as const,
    labelKey: 'launcher.ai',
    color: '#3B82F6',
    description: 'launcher.aiDesc',
    defaultOpen: false,
  },
  {
    key: 'finance' as const,
    labelKey: 'launcher.finance',
    color: '#F97316',
    description: 'launcher.financeDesc',
    defaultOpen: false,
  },
  {
    key: 'nav' as const,
    labelKey: 'launcher.nav',
    color: '#DC2626',
    description: 'launcher.navDesc',
    defaultOpen: false,
  },
];
