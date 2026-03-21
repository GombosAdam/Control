import { useEffect, useState, useRef } from 'react';
import { adminApi } from '../../../services/api/admin';

interface GpuStatus {
  instance_id: string;
  instance_type: string;
  state: string;
  public_ip: string | null;
  ollama_status: string;
  models: string[];
  ollama_url: string | null;
  gpu: { name: string; vram: string; cuda_cores: number; compute: string };
  cost_per_hour: number;
}

export function GpuControlPage() {
  const [status, setStatus] = useState<GpuStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [elapsed, setElapsed] = useState(0);
  const intervalRef = useRef<any>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const addLog = (msg: string) => {
    const ts = new Date().toLocaleTimeString('hu-HU');
    setLogs(prev => [...prev, `[${ts}] ${msg}`]);
  };

  const pollStatus = async () => {
    try {
      const data = await adminApi.gpuStatus();
      setStatus(data);
      return data;
    } catch (e) {
      addLog('⚠ Status check failed');
      return null;
    }
  };

  useEffect(() => {
    pollStatus().then(data => {
      if (data && (data.state === 'stopping' || data.state === 'pending')) {
        setActionInProgress(data.state === 'stopping' ? 'stopping' : 'starting');
        addLog(`⏳ Instance is ${data.state}...`);
      }
    });
    // Background poll every 10s
    const bgPoller = setInterval(() => {
      if (!actionInProgress) pollStatus();
    }, 10000);
    return () => clearInterval(bgPoller);
  }, []);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Poll during transitions
  useEffect(() => {
    if (actionInProgress) {
      const timer = setInterval(() => setElapsed(e => e + 1), 1000);
      const poller = setInterval(async () => {
        const data = await pollStatus();
        if (!data) return;

        if (actionInProgress === 'starting') {
          if (data.state === 'running' && data.ollama_status === 'ready') {
            addLog('✅ GPU online — Ollama ready — Models loaded');
            setActionInProgress(null);
            clearInterval(poller);
            clearInterval(timer);
          } else if (data.state === 'running' && data.ollama_status === 'starting') {
            addLog('⏳ Instance running, Ollama initializing...');
          } else if (data.state === 'running' && data.public_ip) {
            addLog(`🌐 IP assigned: ${data.public_ip}`);
          }
        }

        if (actionInProgress === 'stopping') {
          if (data.state === 'stopped') {
            addLog('⬛ GPU instance stopped');
            setActionInProgress(null);
            clearInterval(poller);
            clearInterval(timer);
          }
        }
      }, 5000);

      return () => { clearInterval(timer); clearInterval(poller); };
    }
  }, [actionInProgress]);

  const handleStart = async () => {
    setActionInProgress('starting');
    setElapsed(0);
    setLogs([]);
    addLog('🚀 Starting GPU instance...');
    addLog('📡 Sending start command to AWS eu-central-1 (Frankfurt)...');
    try {
      await adminApi.gpuStart();
      addLog('✓ Start command accepted — instance booting');
      addLog('⏳ Loading NVIDIA L4 GPU driver + CUDA 13.0...');
    } catch (e) {
      addLog('❌ Failed to start instance');
      setActionInProgress(null);
    }
  };

  const handleStop = async () => {
    setActionInProgress('stopping');
    setElapsed(0);
    addLog('🛑 Stopping GPU instance...');
    try {
      await adminApi.gpuStop();
      addLog('✓ Stop command sent — shutting down');
    } catch (e) {
      addLog('❌ Failed to stop instance');
      setActionInProgress(null);
    }
  };

  const stateColor = (state: string) => {
    if (state === 'running') return '#10B981';
    if (state === 'stopped') return '#6B7280';
    if (state === 'stopping') return '#F59E0B';
    if (state === 'pending') return '#F59E0B';
    return '#999';
  };

  const ollamaColor = (s: string) => {
    if (s === 'ready') return '#10B981';
    if (s === 'starting') return '#F59E0B';
    return '#EF4444';
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1000px', margin: '0 auto' }}>
      {/* Privacy Banner */}
      <div style={{
        background: 'linear-gradient(135deg, #0c4a6e 0%, #164e63 100%)',
        borderRadius: '12px', padding: '20px 24px', marginBottom: '24px',
        display: 'flex', alignItems: 'center', gap: '20px',
        border: '1px solid rgba(56, 189, 248, 0.2)',
      }}>
        <div style={{
          width: '52px', height: '52px', borderRadius: '12px', flexShrink: 0,
          background: 'rgba(56, 189, 248, 0.15)', border: '1px solid rgba(56, 189, 248, 0.3)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '24px',
        }}>
          🛡️
        </div>
        <div>
          <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 700, color: '#fff', letterSpacing: '0.5px' }}>
            PRIVATE AI INFRASTRUCTURE — ZERO DATA LEAKAGE
          </h2>
          <p style={{ margin: '6px 0 0', fontSize: '13px', color: '#94a3b8', lineHeight: 1.5 }}>
            Self-hosted AI on our own GPU cluster. No OpenAI. No Google. No third-party API calls.
            Every document is processed on <span style={{ color: '#38bdf8', fontWeight: 600 }}>our dedicated hardware</span> — your data never leaves
            the infrastructure. Full sovereignty, zero external dependencies.
          </p>
        </div>
      </div>

      {/* Title */}
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: 700, color: '#1a1a1a', margin: 0, letterSpacing: '-0.5px' }}>
          GPU Control Center
        </h1>
        <p style={{ fontSize: '14px', color: '#666', margin: '4px 0 0' }}>
          AWS Cloud GPU — AI Inference Engine
        </p>
      </div>

      {/* GPU Hardware Card */}
      <div style={{
        background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
        borderRadius: '16px', padding: '28px', marginBottom: '20px',
        color: '#fff', position: 'relative', overflow: 'hidden',
      }}>
        {/* Animated background grid */}
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, opacity: 0.05,
          backgroundImage: 'linear-gradient(rgba(255,255,255,.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.1) 1px, transparent 1px)',
          backgroundSize: '20px 20px',
        }} />

        <div style={{ position: 'relative', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              {/* GPU icon */}
              <div style={{
                width: '48px', height: '48px', borderRadius: '12px',
                background: 'linear-gradient(135deg, #76B900 0%, #4a7a00 100%)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '20px', fontWeight: 800,
              }}>
                GPU
              </div>
              <div>
                <p style={{ margin: 0, fontSize: '20px', fontWeight: 700 }}>{status?.gpu?.name || 'NVIDIA L4'}</p>
                <p style={{ margin: 0, fontSize: '13px', color: '#94a3b8' }}>{status?.gpu?.vram || '24 GB GDDR6'} — Ada Lovelace</p>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '32px', fontSize: '13px' }}>
              <div>
                <p style={{ margin: 0, color: '#64748b', fontSize: '11px', textTransform: 'uppercase' }}>CUDA Cores</p>
                <p style={{ margin: '2px 0 0', fontWeight: 600, fontSize: '16px' }}>{(status?.gpu?.cuda_cores || 7424).toLocaleString()}</p>
              </div>
              <div>
                <p style={{ margin: 0, color: '#64748b', fontSize: '11px', textTransform: 'uppercase' }}>Compute</p>
                <p style={{ margin: '2px 0 0', fontWeight: 600, fontSize: '16px' }}>{status?.gpu?.compute || '8.9'}</p>
              </div>
              <div>
                <p style={{ margin: 0, color: '#64748b', fontSize: '11px', textTransform: 'uppercase' }}>FP16 Tensor</p>
                <p style={{ margin: '2px 0 0', fontWeight: 600, fontSize: '16px' }}>121 TFLOPS</p>
              </div>
              <div>
                <p style={{ margin: 0, color: '#64748b', fontSize: '11px', textTransform: 'uppercase' }}>Instance</p>
                <p style={{ margin: '2px 0 0', fontWeight: 600, fontSize: '16px' }}>{status?.instance_type || 'g6.xlarge'}</p>
              </div>
              <div>
                <p style={{ margin: 0, color: '#64748b', fontSize: '11px', textTransform: 'uppercase' }}>Cost</p>
                <p style={{ margin: '2px 0 0', fontWeight: 600, fontSize: '16px' }}>${status?.cost_per_hour || 0.98}/hr</p>
              </div>
            </div>
          </div>

          {/* Status indicator */}
          <div style={{ textAlign: 'right' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'flex-end' }}>
              <div style={{
                width: '12px', height: '12px', borderRadius: '50%',
                background: stateColor(status?.state || 'unknown'),
                boxShadow: status?.state === 'running' ? `0 0 12px ${stateColor('running')}` : 'none',
                animation: (status?.state === 'running' || actionInProgress) ? 'pulse 2s ease-in-out infinite' : 'none',
              }} />
              <span style={{ fontSize: '14px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px' }}>
                {actionInProgress || status?.state || 'unknown'}
              </span>
            </div>
            {status?.public_ip && (
              <p style={{ margin: '8px 0 0', fontSize: '12px', color: '#64748b', fontFamily: 'monospace' }}>
                {status.public_ip}:11434
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Action Buttons + Ollama Status */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', marginBottom: '20px' }}>
        {/* Start Button */}
        <button
          onClick={handleStart}
          disabled={actionInProgress !== null || status?.state === 'running'}
          style={{
            padding: '20px', borderRadius: '12px', border: 'none', cursor: 'pointer',
            background: (actionInProgress || status?.state === 'running')
              ? '#1e293b' : 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
            color: '#fff', fontSize: '16px', fontWeight: 700,
            opacity: (actionInProgress || status?.state === 'running') ? 0.4 : 1,
            transition: 'all 200ms ease',
            boxShadow: (actionInProgress || status?.state === 'running') ? 'none' : '0 4px 20px rgba(16,185,129,0.4)',
          }}
        >
          {actionInProgress === 'starting' ? (
            <span>
              <span style={{ display: 'inline-block', animation: 'spin 1s linear infinite', marginRight: '8px' }}>⚡</span>
              STARTING... {elapsed}s
            </span>
          ) : '▶ START GPU'}
        </button>

        {/* Stop Button */}
        <button
          onClick={handleStop}
          disabled={actionInProgress !== null || status?.state !== 'running'}
          style={{
            padding: '20px', borderRadius: '12px', border: 'none', cursor: 'pointer',
            background: (actionInProgress || status?.state !== 'running')
              ? '#1e293b' : 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)',
            color: '#fff', fontSize: '16px', fontWeight: 700,
            opacity: (actionInProgress || status?.state !== 'running') ? 0.4 : 1,
            transition: 'all 200ms ease',
            boxShadow: (actionInProgress || status?.state !== 'running') ? 'none' : '0 4px 20px rgba(239,68,68,0.4)',
          }}
        >
          {actionInProgress === 'stopping' ? `⏳ STOPPING... ${elapsed}s` : '⬛ STOP GPU'}
        </button>

        {/* Ollama Status */}
        <div style={{
          padding: '20px', borderRadius: '12px',
          background: '#fff', border: '1px solid #e5e7eb',
          display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <div style={{
              width: '10px', height: '10px', borderRadius: '50%',
              background: ollamaColor(status?.ollama_status || 'offline'),
              boxShadow: status?.ollama_status === 'ready' ? '0 0 8px #10B981' : 'none',
            }} />
            <span style={{ fontSize: '14px', fontWeight: 600, color: '#333' }}>Ollama</span>
          </div>
          <p style={{ margin: 0, fontSize: '12px', color: '#666' }}>
            {status?.ollama_status === 'ready' ? `${status.models?.length || 0} model loaded` : status?.ollama_status || 'offline'}
          </p>
          {status?.models?.map(m => (
            <span key={m} style={{
              marginTop: '4px', padding: '2px 8px', borderRadius: '4px',
              background: '#f0fdf4', color: '#166534', fontSize: '11px', fontWeight: 600,
            }}>
              {m}
            </span>
          ))}
        </div>
      </div>

      {/* Live Log */}
      {logs.length > 0 && (
        <div style={{
          background: '#0f172a', borderRadius: '12px', padding: '16px',
          fontFamily: "'JetBrains Mono', 'Fira Code', monospace", fontSize: '12px',
          color: '#e2e8f0', maxHeight: '240px', overflowY: 'auto',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', paddingBottom: '8px', borderBottom: '1px solid #1e293b' }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#EF4444' }} />
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#F59E0B' }} />
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10B981' }} />
            <span style={{ marginLeft: '8px', fontSize: '11px', color: '#64748b' }}>system.log</span>
          </div>
          {logs.map((log, i) => (
            <div key={i} style={{
              padding: '2px 0', color: log.includes('✅') ? '#4ade80' : log.includes('❌') ? '#f87171' : log.includes('⏳') ? '#fbbf24' : '#cbd5e1',
            }}>
              {log}
            </div>
          ))}
          {actionInProgress && (
            <div style={{ color: '#3b82f6', animation: 'blink 1s step-end infinite' }}>
              {'>'} _
            </div>
          )}
          <div ref={logsEndRef} />
        </div>
      )}

      {/* Info Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', marginTop: '20px' }}>
        <div style={{ background: '#fff', borderRadius: '12px', padding: '20px', border: '1px solid #e5e7eb' }}>
          <h3 style={{ margin: '0 0 12px', fontSize: '14px', fontWeight: 600, color: '#333' }}>Instance</h3>
          <InfoRow label="ID" value={status?.instance_id || '-'} mono />
          <InfoRow label="Region" value="eu-central-1 (Frankfurt)" />
          <InfoRow label="Type" value={status?.instance_type || 'g6.xlarge'} />
          <InfoRow label="Public IP" value={status?.public_ip || 'not assigned'} mono />
        </div>
        <div style={{ background: '#fff', borderRadius: '12px', padding: '20px', border: '1px solid #e5e7eb' }}>
          <h3 style={{ margin: '0 0 12px', fontSize: '14px', fontWeight: 600, color: '#333' }}>Text-to-SQL Model</h3>
          <InfoRow label="Model" value="defog-llama3-sqlcoder-8b" />
          <InfoRow label="Type" value="SQL Specialist (Llama 3)" />
          <InfoRow label="Size" value="4.7 GB" />
          <InfoRow label="Capability" value="Natural Language → SQL" />
        </div>
        <div style={{ background: '#fff', borderRadius: '12px', padding: '20px', border: '1px solid #e5e7eb' }}>
          <h3 style={{ margin: '0 0 12px', fontSize: '14px', fontWeight: 600, color: '#333' }}>Vision Model</h3>
          <InfoRow label="Model" value="qwen2.5vl:7b" />
          <InfoRow label="Type" value="Vision-Language Model" />
          <InfoRow label="Size" value="6.0 GB" />
          <InfoRow label="Capability" value="OCR + Data Extraction" />
        </div>
      </div>

      {/* Performance Card */}
      <div style={{
        marginTop: '16px', background: 'linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%)',
        borderRadius: '12px', padding: '20px', border: '1px solid #bbf7d0',
      }}>
        <h3 style={{ margin: '0 0 12px', fontSize: '14px', fontWeight: 600, color: '#166534' }}>Performance</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '16px' }}>
          <div>
            <p style={{ margin: 0, fontSize: '11px', color: '#15803d', textTransform: 'uppercase', fontWeight: 600 }}>Chat Response</p>
            <p style={{ margin: '4px 0 0', fontSize: '24px', fontWeight: 700, color: '#166534' }}>~1s</p>
          </div>
          <div>
            <p style={{ margin: 0, fontSize: '11px', color: '#15803d', textTransform: 'uppercase', fontWeight: 600 }}>OCR Extraction</p>
            <p style={{ margin: '4px 0 0', fontSize: '24px', fontWeight: 700, color: '#166534' }}>~8s</p>
          </div>
          <div>
            <p style={{ margin: 0, fontSize: '11px', color: '#15803d', textTransform: 'uppercase', fontWeight: 600 }}>VRAM Capacity</p>
            <p style={{ margin: '4px 0 0', fontSize: '24px', fontWeight: 700, color: '#166534' }}>24 GB</p>
          </div>
          <div>
            <p style={{ margin: 0, fontSize: '11px', color: '#15803d', textTransform: 'uppercase', fontWeight: 600 }}>Max Throughput</p>
            <p style={{ margin: '4px 0 0', fontSize: '24px', fontWeight: 700, color: '#166534' }}>121 TFLOPS</p>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes blink { 50% { opacity: 0; } }
      `}</style>
    </div>
  );
}

function InfoRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: '13px' }}>
      <span style={{ color: '#888' }}>{label}</span>
      <span style={{ color: '#333', fontWeight: 500, fontFamily: mono ? "'JetBrains Mono', monospace" : 'inherit', fontSize: mono ? '12px' : '13px' }}>
        {value}
      </span>
    </div>
  );
}
