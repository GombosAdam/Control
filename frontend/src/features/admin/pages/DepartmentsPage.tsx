import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, Pencil, Trash2, Save, X, ChevronRight, Users, Wallet } from 'lucide-react';
import { departmentsApi } from '../../../services/api/departments';
import { adminApi } from '../../../services/api/admin';

interface Department {
  id: string;
  name: string;
  code: string;
  parent_id: string | null;
  manager_id: string | null;
  manager_name: string | null;
  created_at: string;
  updated_at: string;
}

interface User {
  id: string;
  full_name: string;
  email: string;
  role: string;
  department_id: string | null;
}

const emptyForm = { name: '', code: '', parent_id: '', manager_id: '' };

export function DepartmentsPage() {
  const { t } = useTranslation();
  const [departments, setDepartments] = useState<Department[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    const [depts, userData] = await Promise.all([
      departmentsApi.list(),
      adminApi.listUsers({ limit: 200 }),
    ]);
    setDepartments(depts);
    setUsers(userData.items);
  };

  useEffect(() => { load(); }, []);

  const startEdit = (dept: Department) => {
    setEditingId(dept.id);
    setForm({
      name: dept.name,
      code: dept.code,
      parent_id: dept.parent_id || '',
      manager_id: dept.manager_id || '',
    });
    setCreating(false);
    setError('');
  };

  const startCreate = () => {
    setCreating(true);
    setEditingId(null);
    setForm(emptyForm);
    setError('');
  };

  const cancel = () => {
    setEditingId(null);
    setCreating(false);
    setForm(emptyForm);
    setError('');
  };

  const handleSave = async () => {
    setError('');
    if (!form.name.trim() || !form.code.trim()) {
      setError('Név és kód kötelező');
      return;
    }
    try {
      const payload = {
        name: form.name,
        code: form.code,
        parent_id: form.parent_id || undefined,
        manager_id: form.manager_id || undefined,
      };
      if (creating) {
        await departmentsApi.create(payload);
      } else if (editingId) {
        await departmentsApi.update(editingId, payload);
      }
      cancel();
      await load();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.response?.data?.error || 'Hiba');
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Biztosan törli az osztályt?')) return;
    try {
      await departmentsApi.delete(id);
      if (editingId === id) cancel();
      await load();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Nem sikerült törölni');
    }
  };

  // Build hierarchy for display
  const getParentName = (parentId: string | null) => {
    if (!parentId) return null;
    return departments.find(d => d.id === parentId)?.name || '-';
  };

  const getMemberCount = (deptId: string) => users.filter(u => u.department_id === deptId).length;

  return (
    <div style={{ padding: '24px', maxWidth: '1200px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 600, margin: 0 }}>Szervezeti felépítés</h1>
        <button onClick={startCreate} style={{
          display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px',
          background: '#06B6D4', color: '#fff', border: 'none', borderRadius: '6px',
          cursor: 'pointer', fontSize: '13px', fontWeight: 500,
        }}>
          <Plus size={14} /> Új osztály
        </button>
      </div>

      {error && (
        <div style={{ padding: '10px 16px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', marginBottom: '16px', color: '#991b1b', fontSize: '13px' }}>
          {error}
        </div>
      )}

      {/* Create form */}
      {creating && (
        <div style={{ background: '#fff', borderRadius: '8px', padding: '20px', marginBottom: '16px', border: '2px solid #06B6D4', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <h3 style={{ margin: '0 0 16px', fontSize: '14px', fontWeight: 600, color: '#333' }}>Új osztály létrehozása</h3>
          <FormFields form={form} setForm={setForm} departments={departments} users={users} excludeId={null} />
          <div style={{ display: 'flex', gap: '8px', marginTop: '16px' }}>
            <button onClick={handleSave} style={saveBtnStyle}><Save size={14} /> Mentés</button>
            <button onClick={cancel} style={cancelBtnStyle}><X size={14} /> Mégse</button>
          </div>
        </div>
      )}

      {/* Department table */}
      <div style={{ background: '#fff', borderRadius: '8px', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
              {['Kód', 'Név', 'Szülő osztály', 'Vezető', 'Tagok', ''].map(h => (
                <th key={h} style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: 600, color: '#666', textTransform: 'uppercase' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {departments.map(dept => {
              const isEditing = editingId === dept.id;
              if (isEditing) {
                return (
                  <tr key={dept.id} style={{ borderBottom: '1px solid #f3f4f6', background: '#eff6ff' }}>
                    <td colSpan={6} style={{ padding: '16px' }}>
                      <FormFields form={form} setForm={setForm} departments={departments} users={users} excludeId={dept.id} />
                      <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                        <button onClick={handleSave} style={saveBtnStyle}><Save size={14} /> Mentés</button>
                        <button onClick={cancel} style={cancelBtnStyle}><X size={14} /> Mégse</button>
                      </div>
                    </td>
                  </tr>
                );
              }
              const memberCount = getMemberCount(dept.id);
              return (
                <tr key={dept.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                  <td style={{ padding: '12px 16px', fontSize: '14px' }}>
                    <code style={{ background: '#f3f4f6', padding: '2px 6px', borderRadius: '4px', fontSize: '12px', fontWeight: 600 }}>{dept.code}</code>
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: '14px', fontWeight: 500 }}>{dept.name}</td>
                  <td style={{ padding: '12px 16px', fontSize: '14px', color: '#666' }}>
                    {getParentName(dept.parent_id) ? (
                      <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <ChevronRight size={12} /> {getParentName(dept.parent_id)}
                      </span>
                    ) : '—'}
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: '14px' }}>
                    {dept.manager_name ? (
                      <span style={{ padding: '2px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 500, background: '#d1fae5', color: '#065f46' }}>
                        {dept.manager_name}
                      </span>
                    ) : (
                      <span style={{ color: '#EF4444', fontSize: '12px' }}>Nincs vezető!</span>
                    )}
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: '14px', color: '#666' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Users size={12} /> {memberCount}
                    </span>
                  </td>
                  <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                    <div style={{ display: 'flex', gap: '4px', justifyContent: 'flex-end' }}>
                      <button onClick={() => startEdit(dept)} style={actionBtnStyle} title="Szerkesztés"><Pencil size={13} /></button>
                      <button onClick={() => handleDelete(dept.id)} style={{ ...actionBtnStyle, color: '#EF4444' }} title="Törlés"><Trash2 size={13} /></button>
                    </div>
                  </td>
                </tr>
              );
            })}
            {departments.length === 0 && (
              <tr><td colSpan={6} style={{ padding: '40px', textAlign: 'center', color: '#999' }}>Nincsenek osztályok</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Budget Master */}
      {departments.length > 0 && (
        <div style={{ marginTop: '24px' }}>
          <h2 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Wallet size={18} /> Budget sor master
          </h2>
          <p style={{ fontSize: '12px', color: '#888', marginBottom: '12px' }}>
            Osztályonként beállítható, mely számla kódokra (budget sorokra) adhat fel megrendelést. Ha üres, minden budget sor elérhető.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', gap: '12px' }}>
            {departments.map(dept => (
              <BudgetMasterCard key={dept.id} department={dept} />
            ))}
          </div>
        </div>
      )}

      {/* Department members quick view */}
      {departments.length > 0 && (
        <div style={{ marginTop: '24px' }}>
          <h2 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '12px' }}>Tagok osztályonként</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '12px' }}>
            {departments.map(dept => {
              const members = users.filter(u => u.department_id === dept.id);
              return (
                <div key={dept.id} style={{ background: '#fff', borderRadius: '8px', padding: '14px', border: '1px solid #e5e7eb' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <span style={{ fontWeight: 600, fontSize: '14px' }}>{dept.name}</span>
                    <code style={{ fontSize: '11px', color: '#888' }}>{dept.code}</code>
                  </div>
                  {dept.manager_name && (
                    <div style={{ fontSize: '12px', color: '#065f46', marginBottom: '6px' }}>
                      Vezető: {dept.manager_name}
                    </div>
                  )}
                  {members.length > 0 ? members.map(m => (
                    <div key={m.id} style={{ fontSize: '12px', color: '#666', padding: '2px 0', display: 'flex', justifyContent: 'space-between' }}>
                      <span>{m.full_name}</span>
                      <span style={{ padding: '0 6px', borderRadius: '8px', fontSize: '10px', background: '#e0e7ff', color: '#4338ca' }}>{m.role}</span>
                    </div>
                  )) : (
                    <div style={{ fontSize: '12px', color: '#999', fontStyle: 'italic' }}>Nincs tag</div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function FormFields({ form, setForm, departments, users, excludeId }: {
  form: typeof emptyForm;
  setForm: (f: typeof emptyForm) => void;
  departments: Department[];
  users: User[];
  excludeId: string | null;
}) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
      <div>
        <label style={labelStyle}>Név</label>
        <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} style={inputStyle} placeholder="pl. Pénzügy" />
      </div>
      <div>
        <label style={labelStyle}>Kód</label>
        <input value={form.code} onChange={e => setForm({ ...form, code: e.target.value })} style={inputStyle} placeholder="pl. FIN" />
      </div>
      <div>
        <label style={labelStyle}>Szülő osztály</label>
        <select value={form.parent_id} onChange={e => setForm({ ...form, parent_id: e.target.value })} style={inputStyle}>
          <option value="">— Nincs (felső szintű) —</option>
          {departments.filter(d => d.id !== excludeId).map(d => (
            <option key={d.id} value={d.id}>{d.name} ({d.code})</option>
          ))}
        </select>
      </div>
      <div>
        <label style={labelStyle}>Vezető</label>
        <select value={form.manager_id} onChange={e => setForm({ ...form, manager_id: e.target.value })} style={inputStyle}>
          <option value="">— Válassz vezetőt —</option>
          {users.filter(u => u.role !== 'reviewer').map(u => (
            <option key={u.id} value={u.id}>{u.full_name} ({u.role})</option>
          ))}
        </select>
      </div>
    </div>
  );
}

interface BudgetMasterItem {
  id: string;
  account_code: string;
  account_name: string;
  is_active: boolean;
}

function BudgetMasterCard({ department }: { department: Department }) {
  const [items, setItems] = useState<BudgetMasterItem[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [newCode, setNewCode] = useState('');
  const [newName, setNewName] = useState('');
  const [saving, setSaving] = useState(false);

  const loadMaster = async () => {
    const data = await departmentsApi.getBudgetMaster(department.id);
    setItems(data);
    setLoaded(true);
  };

  useEffect(() => { if (expanded && !loaded) loadMaster(); }, [expanded]);

  const handleAdd = async () => {
    if (!newCode.trim()) return;
    const updated = [...items, { id: '', account_code: newCode.trim(), account_name: newName.trim() || newCode.trim(), is_active: true }];
    setSaving(true);
    try {
      const result = await departmentsApi.setBudgetMaster(department.id, updated.map(e => ({ account_code: e.account_code, account_name: e.account_name, is_active: e.is_active })));
      setItems(result);
      setNewCode('');
      setNewName('');
    } catch { /* ignore */ }
    setSaving(false);
  };

  const handleRemove = async (code: string) => {
    const updated = items.filter(i => i.account_code !== code);
    setSaving(true);
    try {
      const result = await departmentsApi.setBudgetMaster(department.id, updated.map(e => ({ account_code: e.account_code, account_name: e.account_name, is_active: e.is_active })));
      setItems(result);
    } catch { /* ignore */ }
    setSaving(false);
  };

  return (
    <div style={{ background: '#fff', borderRadius: '8px', border: '1px solid #e5e7eb', overflow: 'hidden' }}>
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          width: '100%', padding: '12px 16px', display: 'flex', justifyContent: 'space-between',
          alignItems: 'center', background: 'transparent', border: 'none', cursor: 'pointer', textAlign: 'left',
        }}
      >
        <div>
          <span style={{ fontWeight: 600, fontSize: '14px' }}>{department.name}</span>
          <code style={{ fontSize: '11px', color: '#888', marginLeft: '8px' }}>{department.code}</code>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {loaded && (
            <span style={{
              fontSize: '11px', padding: '2px 8px', borderRadius: '10px',
              background: items.length > 0 ? '#d1fae5' : '#f3f4f6',
              color: items.length > 0 ? '#065f46' : '#999',
            }}>
              {items.length > 0 ? `${items.length} sor` : 'Nincs szűrés'}
            </span>
          )}
          <ChevronRight size={14} style={{ color: '#999', transform: expanded ? 'rotate(90deg)' : 'none', transition: '150ms' }} />
        </div>
      </button>
      {expanded && (
        <div style={{ padding: '0 16px 14px', borderTop: '1px solid #f3f4f6' }}>
          {items.length > 0 && (
            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '8px', fontSize: '12px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                  <th style={{ padding: '4px 8px', textAlign: 'left', color: '#888', fontWeight: 600, fontSize: '10px', textTransform: 'uppercase' }}>Kód</th>
                  <th style={{ padding: '4px 8px', textAlign: 'left', color: '#888', fontWeight: 600, fontSize: '10px', textTransform: 'uppercase' }}>Megnevezés</th>
                  <th style={{ width: '30px' }}></th>
                </tr>
              </thead>
              <tbody>
                {items.map(item => (
                  <tr key={item.account_code} style={{ borderBottom: '1px solid #f9fafb' }}>
                    <td style={{ padding: '4px 8px' }}>
                      <code style={{ background: '#f3f4f6', padding: '1px 4px', borderRadius: '3px', fontSize: '11px' }}>{item.account_code}</code>
                    </td>
                    <td style={{ padding: '4px 8px', color: '#555' }}>{item.account_name}</td>
                    <td style={{ padding: '4px' }}>
                      <button onClick={() => handleRemove(item.account_code)} disabled={saving}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#EF4444', padding: '2px' }}>
                        <Trash2 size={12} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div style={{ display: 'flex', gap: '6px', marginTop: '10px', alignItems: 'center' }}>
            <input value={newCode} onChange={e => setNewCode(e.target.value)} placeholder="Számla kód (pl. 511)"
              style={{ ...inputStyle, width: '100px', padding: '6px 8px', fontSize: '12px' }} />
            <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="Megnevezés"
              style={{ ...inputStyle, flex: 1, padding: '6px 8px', fontSize: '12px' }} />
            <button onClick={handleAdd} disabled={saving || !newCode.trim()}
              style={{ padding: '6px 12px', background: '#10B981', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '11px', fontWeight: 600, whiteSpace: 'nowrap' }}>
              <Plus size={12} /> Hozzáad
            </button>
          </div>
          {items.length === 0 && loaded && (
            <div style={{ fontSize: '11px', color: '#999', marginTop: '6px', fontStyle: 'italic' }}>
              Nincs szűrés — az osztály minden jóváhagyott budget sort lát megrendeléskor.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const inputStyle: React.CSSProperties = { width: '100%', padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '13px', boxSizing: 'border-box' };
const labelStyle: React.CSSProperties = { display: 'block', fontSize: '11px', fontWeight: 600, color: '#555', marginBottom: '4px', textTransform: 'uppercase' };
const saveBtnStyle: React.CSSProperties = { display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px', background: '#10B981', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '13px', fontWeight: 500 };
const cancelBtnStyle: React.CSSProperties = { display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px', background: '#fff', color: '#666', border: '1px solid #d1d5db', borderRadius: '6px', cursor: 'pointer', fontSize: '13px' };
const actionBtnStyle: React.CSSProperties = { padding: '6px 8px', background: '#f3f4f6', border: '1px solid #e5e7eb', borderRadius: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center', color: '#666' };
