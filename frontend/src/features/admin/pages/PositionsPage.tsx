import { useEffect, useState } from 'react';
import { Plus, Save, X, Trash2, Pencil, GitBranch } from 'lucide-react';
import { positionsApi } from '../../../services/api/positions';
import { departmentsApi } from '../../../services/api/departments';

interface Position {
  id: string;
  name: string;
  department_id: string;
  department_name: string | null;
  reports_to_id: string | null;
  reports_to_name: string | null;
  holder_id: string | null;
  holder_name: string | null;
}

interface Department {
  id: string;
  name: string;
  code: string;
}

const emptyForm = { name: '', department_id: '', reports_to_id: '' };

export function PositionsPage() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    const [pos, depts] = await Promise.all([
      positionsApi.list(),
      departmentsApi.list(),
    ]);
    setPositions(pos);
    setDepartments(depts);
  };

  useEffect(() => { load(); }, []);

  const startEdit = (pos: Position) => {
    setEditingId(pos.id);
    setForm({ name: pos.name, department_id: pos.department_id, reports_to_id: pos.reports_to_id || '' });
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
    if (!form.name.trim() || !form.department_id) {
      setError('Név és osztály kötelező');
      return;
    }
    try {
      const payload = {
        name: form.name,
        department_id: form.department_id,
        reports_to_id: form.reports_to_id || undefined,
      };
      if (creating) {
        await positionsApi.create(payload);
      } else if (editingId) {
        await positionsApi.update(editingId, payload);
      }
      cancel();
      await load();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.response?.data?.error || 'Hiba');
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Biztosan törli a pozíciót?')) return;
    try {
      await positionsApi.delete(id);
      if (editingId === id) cancel();
      await load();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Nem sikerült törölni');
    }
  };

  // Group positions by department
  const grouped = departments
    .map(d => ({
      dept: d,
      positions: positions.filter(p => p.department_id === d.id),
    }))
    .filter(g => g.positions.length > 0);

  // Positions with no department match (safety)
  const orphans = positions.filter(p => !departments.find(d => d.id === p.department_id));

  return (
    <div style={{ padding: '24px', maxWidth: '1200px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 600, margin: 0 }}>Pozíciók</h1>
        <button onClick={startCreate} style={{
          display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px',
          background: '#06B6D4', color: '#fff', border: 'none', borderRadius: '6px',
          cursor: 'pointer', fontSize: '13px', fontWeight: 500,
        }}>
          <Plus size={14} /> Új pozíció
        </button>
      </div>

      {error && (
        <div style={{ padding: '10px 16px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', marginBottom: '16px', color: '#991b1b', fontSize: '13px' }}>
          {error}
        </div>
      )}

      {creating && (
        <div style={{ background: '#fff', borderRadius: '8px', padding: '20px', marginBottom: '16px', border: '2px solid #06B6D4', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <h3 style={{ margin: '0 0 16px', fontSize: '14px', fontWeight: 600 }}>Új pozíció</h3>
          <FormFields form={form} setForm={setForm} departments={departments} positions={positions} excludeId={null} />
          <div style={{ display: 'flex', gap: '8px', marginTop: '16px' }}>
            <button onClick={handleSave} style={saveBtnStyle}><Save size={14} /> Mentés</button>
            <button onClick={cancel} style={cancelBtnStyle}><X size={14} /> Mégse</button>
          </div>
        </div>
      )}

      {/* Positions table */}
      <div style={{ background: '#fff', borderRadius: '8px', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
              {['Pozíció', 'Osztály', 'Felettes pozíció', 'Betöltő', ''].map(h => (
                <th key={h} style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: 600, color: '#666', textTransform: 'uppercase' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {positions.map(pos => {
              if (editingId === pos.id) {
                return (
                  <tr key={pos.id} style={{ borderBottom: '1px solid #f3f4f6', background: '#eff6ff' }}>
                    <td colSpan={5} style={{ padding: '16px' }}>
                      <FormFields form={form} setForm={setForm} departments={departments} positions={positions} excludeId={pos.id} />
                      <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                        <button onClick={handleSave} style={saveBtnStyle}><Save size={14} /> Mentés</button>
                        <button onClick={cancel} style={cancelBtnStyle}><X size={14} /> Mégse</button>
                      </div>
                    </td>
                  </tr>
                );
              }
              return (
                <tr key={pos.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                  <td style={{ padding: '12px 16px', fontSize: '14px', fontWeight: 500 }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <GitBranch size={14} style={{ color: '#06B6D4' }} />
                      {pos.name}
                    </span>
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: '14px', color: '#666' }}>
                    {pos.department_name || '—'}
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: '14px' }}>
                    {pos.reports_to_name ? (
                      <span style={{ padding: '2px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 500, background: '#e0e7ff', color: '#4338ca' }}>
                        {pos.reports_to_name}
                      </span>
                    ) : (
                      <span style={{ color: '#999', fontSize: '12px' }}>— Legfelső szint —</span>
                    )}
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: '14px' }}>
                    {pos.holder_name ? (
                      <span style={{ padding: '2px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 500, background: '#d1fae5', color: '#065f46' }}>
                        {pos.holder_name}
                      </span>
                    ) : (
                      <span style={{ color: '#EF4444', fontSize: '12px' }}>Betöltetlen</span>
                    )}
                  </td>
                  <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                    <div style={{ display: 'flex', gap: '4px', justifyContent: 'flex-end' }}>
                      <button onClick={() => startEdit(pos)} style={actionBtnStyle} title="Szerkesztés"><Pencil size={13} /></button>
                      <button onClick={() => handleDelete(pos.id)} style={{ ...actionBtnStyle, color: '#EF4444' }} title="Törlés"><Trash2 size={13} /></button>
                    </div>
                  </td>
                </tr>
              );
            })}
            {positions.length === 0 && (
              <tr><td colSpan={5} style={{ padding: '40px', textAlign: 'center', color: '#999' }}>Nincsenek pozíciók</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Hierarchy view */}
      {grouped.length > 0 && (
        <div style={{ marginTop: '24px' }}>
          <h2 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '12px' }}>Hierarchia osztályonként</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '12px' }}>
            {grouped.map(({ dept, positions: deptPositions }) => {
              // Build tree: top-level first, then children
              const roots = deptPositions.filter(p => !p.reports_to_id || !deptPositions.find(pp => pp.id === p.reports_to_id));
              const renderNode = (p: Position, depth: number): React.ReactNode => {
                const children = deptPositions.filter(c => c.reports_to_id === p.id);
                return (
                  <div key={p.id}>
                    <div style={{ paddingLeft: depth * 20, fontSize: '13px', padding: '4px 0 4px ' + (depth * 20) + 'px', display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ fontWeight: depth === 0 ? 600 : 400 }}>
                        {depth > 0 && '└ '}{p.name}
                      </span>
                      <span style={{
                        fontSize: '11px',
                        color: p.holder_name ? '#065f46' : '#EF4444',
                      }}>
                        {p.holder_name || 'betöltetlen'}
                      </span>
                    </div>
                    {children.map(c => renderNode(c, depth + 1))}
                  </div>
                );
              };
              return (
                <div key={dept.id} style={{ background: '#fff', borderRadius: '8px', padding: '14px', border: '1px solid #e5e7eb' }}>
                  <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: '8px', display: 'flex', justifyContent: 'space-between' }}>
                    <span>{dept.name}</span>
                    <code style={{ fontSize: '11px', color: '#888' }}>{dept.code}</code>
                  </div>
                  {roots.map(r => renderNode(r, 0))}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function FormFields({ form, setForm, departments, positions, excludeId }: {
  form: typeof emptyForm;
  setForm: (f: typeof emptyForm) => void;
  departments: Department[];
  positions: Position[];
  excludeId: string | null;
}) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
      <div>
        <label style={labelStyle}>Pozíció neve</label>
        <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} style={inputStyle} placeholder="pl. Beszerzési munkatárs" />
      </div>
      <div>
        <label style={labelStyle}>Osztály</label>
        <select value={form.department_id} onChange={e => setForm({ ...form, department_id: e.target.value })} style={inputStyle}>
          <option value="">— Válassz —</option>
          {departments.map(d => (
            <option key={d.id} value={d.id}>{d.name} ({d.code})</option>
          ))}
        </select>
      </div>
      <div>
        <label style={labelStyle}>Felettes pozíció</label>
        <select value={form.reports_to_id} onChange={e => setForm({ ...form, reports_to_id: e.target.value })} style={inputStyle}>
          <option value="">— Nincs (legfelső) —</option>
          {positions.filter(p => p.id !== excludeId).map(p => (
            <option key={p.id} value={p.id}>{p.name} ({p.department_name})</option>
          ))}
        </select>
      </div>
    </div>
  );
}

const inputStyle: React.CSSProperties = { width: '100%', padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '13px', boxSizing: 'border-box' };
const labelStyle: React.CSSProperties = { display: 'block', fontSize: '11px', fontWeight: 600, color: '#555', marginBottom: '4px', textTransform: 'uppercase' };
const saveBtnStyle: React.CSSProperties = { display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px', background: '#10B981', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '13px', fontWeight: 500 };
const cancelBtnStyle: React.CSSProperties = { display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px', background: '#fff', color: '#666', border: '1px solid #d1d5db', borderRadius: '6px', cursor: 'pointer', fontSize: '13px' };
const actionBtnStyle: React.CSSProperties = { padding: '6px 8px', background: '#f3f4f6', border: '1px solid #e5e7eb', borderRadius: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center', color: '#666' };
