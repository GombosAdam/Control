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
  TrendingUp,
  Receipt,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

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
}

export const modules: Record<string, ModuleDefinition> = {
  dashboard: {
    nameKey: 'modules.dashboard',
    color: '#3B82F6',
    icon: LayoutDashboard,
    routes: ['/dashboard'],
    items: [
      { icon: LayoutDashboard, path: '/dashboard', labelKey: 'nav.dashboard' },
    ],
  },
  invoices: {
    nameKey: 'modules.invoices',
    color: '#10B981',
    icon: FileText,
    routes: ['/invoices'],
    items: [
      { icon: FileText, path: '/invoices', labelKey: 'nav.invoices' },
      { icon: Upload, path: '/invoices/upload', labelKey: 'nav.upload' },
      { icon: Loader, path: '/invoices/processing', labelKey: 'nav.processing' },
    ],
  },
  extraction: {
    nameKey: 'modules.extraction',
    color: '#8B5CF6',
    icon: ScanSearch,
    routes: ['/extraction'],
    items: [
      { icon: ListChecks, path: '/extraction/queue', labelKey: 'nav.queue' },
      { icon: Eye, path: '/extraction/review', labelKey: 'nav.review' },
    ],
  },
  partners: {
    nameKey: 'modules.partners',
    color: '#F59E0B',
    icon: Building2,
    routes: ['/partners'],
    items: [
      { icon: Building2, path: '/partners', labelKey: 'nav.partners' },
      { icon: Truck, path: '/partners/suppliers', labelKey: 'nav.suppliers' },
      { icon: UsersIcon, path: '/partners/customers', labelKey: 'nav.customers' },
    ],
  },
  reports: {
    nameKey: 'modules.reports',
    color: '#EC4899',
    icon: BarChart3,
    routes: ['/reports'],
    items: [
      { icon: BarChart3, path: '/reports', labelKey: 'nav.reports' },
      { icon: TrendingUp, path: '/reports/monthly', labelKey: 'nav.monthly' },
      { icon: Receipt, path: '/reports/vat', labelKey: 'nav.vat' },
      { icon: Truck, path: '/reports/suppliers', labelKey: 'nav.supplierReport' },
    ],
  },
  admin: {
    nameKey: 'modules.admin',
    color: '#6B7280',
    icon: Settings,
    routes: ['/admin'],
    items: [
      { icon: UsersIcon, path: '/admin/users', labelKey: 'nav.users' },
      { icon: Sliders, path: '/admin/settings', labelKey: 'nav.settings' },
      { icon: Monitor, path: '/admin/system', labelKey: 'nav.system' },
      { icon: ClipboardList, path: '/admin/audit', labelKey: 'nav.audit' },
    ],
  },
};

export type ModuleKey = keyof typeof modules;
