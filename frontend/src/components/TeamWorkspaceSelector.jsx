import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';

export default function TeamWorkspaceSelector({ activeWorkspaceId, onSelectWorkspace }) {
  const [workspaces, setWorkspaces] = useState([]);

  useEffect(() => {
    api.listWorkspaces()
      .then((data) => {
        if (data && data.length > 0) {
          setWorkspaces(data);
        } else {
          setWorkspaces([
            { id: 'default-workspace', name: 'Primary Enterprise Workspace', slug: 'primary' },
            { id: 'ws-research-dept', name: 'Strategic R&D Workspace', slug: 'rand-d' },
            { id: 'ws-finance-dept', name: 'M&A Finance & Legal Workspace', slug: 'ma-legal' },
          ]);
        }
      })
      .catch(() => {
        setWorkspaces([
          { id: 'default-workspace', name: 'Primary Enterprise Workspace', slug: 'primary' },
          { id: 'ws-research-dept', name: 'Strategic R&D Workspace', slug: 'rand-d' },
          { id: 'ws-finance-dept', name: 'M&A Finance & Legal Workspace', slug: 'ma-legal' },
        ]);
      });
  }, []);

  return (
    <div style={{ padding: '12px 16px', borderBottom: '1px solid #1e293b' }}>
      <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', color: '#64748b', fontWeight: '700', marginBottom: '6px' }}>
        Active Workspace
      </label>
      <select
        value={activeWorkspaceId || 'default-workspace'}
        onChange={(e) => onSelectWorkspace(e.target.value)}
        style={{
          width: '100%',
          padding: '8px 10px',
          backgroundColor: '#0f172a',
          border: '1px solid #334155',
          borderRadius: '6px',
          color: '#38bdf8',
          fontSize: '13px',
          fontWeight: '600',
          cursor: 'pointer',
        }}
      >
        {workspaces.map((w) => (
          <option key={w.id} value={w.id}>
             {w.name}
          </option>
        ))}
      </select>
    </div>
  );
}
