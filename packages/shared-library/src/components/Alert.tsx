import React from 'react';

export interface AlertProps {
  title?: string;
  children: React.ReactNode;
  variant?: 'info' | 'success' | 'warning' | 'error';
  onClose?: () => void;
}

const variantStyles: Record<string, { background: string; border: string; color: string; icon: string }> = {
  info: { background: '#ebf8ff', border: '#90cdf4', color: '#2b6cb0', icon: 'ℹ️' },
  success: { background: '#f0fff4', border: '#9ae6b4', color: '#276749', icon: '✓' },
  warning: { background: '#fffaf0', border: '#fbd38d', color: '#c05621', icon: '⚠' },
  error: { background: '#fff5f5', border: '#feb2b2', color: '#c53030', icon: '✕' },
};

export const Alert: React.FC<AlertProps> = ({
  title,
  children,
  variant = 'info',
  onClose,
}) => {
  const { background, border, color, icon } = variantStyles[variant];

  return (
    <div
      style={{
        display: 'flex',
        gap: '12px',
        padding: '16px',
        background,
        border: `1px solid ${border}`,
        borderRadius: '8px',
        color,
      }}
    >
      <span style={{ fontSize: '1.25rem' }}>{icon}</span>
      <div style={{ flex: 1 }}>
        {title && (
          <div style={{ fontWeight: 600, marginBottom: '4px' }}>{title}</div>
        )}
        <div style={{ fontSize: '0.875rem' }}>{children}</div>
      </div>
      {onClose && (
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color,
            fontSize: '1.25rem',
            padding: 0,
          }}
        >
          ×
        </button>
      )}
    </div>
  );
};
