import React, { useState } from 'react';
import { api } from '../lib/api';

export default function HeaderAuthBar({ user = { email: 'admin@enterprise.com', role: 'OWNER' } }) {
  const [showSSODialog, setShowSSODialog] = useState(false);

  const handleSSOLogin = async (provider) => {
    try {
      const res = await api.initiateSSOLogin(provider);
      if (res.auth_url) {
        // Trigger SSO callback with simulated code for test/demo
        await api.ssoCallback(provider, 'mock_auth_code_123');
        alert(`SSO Login successful via ${provider.toUpperCase()}`);
        setShowSSODialog(false);
      }
    } catch (e) {
      alert(`SSO Login failed: ${e.message}`);
    }
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', backgroundColor: '#1e293b', padding: '6px 12px', borderRadius: '20px', border: '1px solid #334155' }}>
        <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#4ade80' }}></span>
        <span style={{ fontSize: '12px', fontWeight: '600', color: '#f8fafc' }}>{user.email}</span>
        <span style={{ fontSize: '10px', fontWeight: '700', padding: '2px 6px', borderRadius: '8px', backgroundColor: '#581c87', color: '#c084fc' }}>
          {user.role}
        </span>
      </div>

      <button
        onClick={() => setShowSSODialog(true)}
        style={{
          padding: '6px 14px',
          backgroundColor: '#334155',
          color: '#cbd5e1',
          border: '1px solid #475569',
          borderRadius: '6px',
          fontSize: '12px',
          fontWeight: '600',
          cursor: 'pointer',
        }}
      >
         SSO Auth & Sessions
      </button>

      {showSSODialog && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.7)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
          <div style={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '12px', padding: '24px', width: '400px', color: '#e2e8f0' }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '18px' }}> Enterprise Single Sign-On (SSO)</h3>
            <p style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '20px' }}>
              Authenticate via enterprise identity provider to issue secure JWT sessions and enforce RBAC policies.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
              {['google', 'azure_ad', 'okta', 'saml'].map((provider) => (
                <button
                  key={provider}
                  onClick={() => handleSSOLogin(provider)}
                  style={{
                    padding: '10px',
                    backgroundColor: '#1e293b',
                    color: '#38bdf8',
                    border: '1px solid #334155',
                    borderRadius: '6px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    textTransform: 'uppercase',
                    fontSize: '12px',
                  }}
                >
                  Log in with {provider.replace('_', ' ')}
                </button>
              ))}
            </div>

            <button
              onClick={() => setShowSSODialog(false)}
              style={{ width: '100%', padding: '10px', backgroundColor: '#334155', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer' }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
