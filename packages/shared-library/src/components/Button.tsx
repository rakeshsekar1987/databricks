import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  children: React.ReactNode;
}

const variantStyles: Record<string, React.CSSProperties> = {
  primary: {
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    color: 'white',
    border: 'none',
  },
  secondary: {
    background: '#f7fafc',
    color: '#2d3748',
    border: '1px solid #e2e8f0',
  },
  danger: {
    background: '#e53e3e',
    color: 'white',
    border: 'none',
  },
  ghost: {
    background: 'transparent',
    color: '#667eea',
    border: 'none',
  },
};

const sizeStyles: Record<string, React.CSSProperties> = {
  sm: { padding: '6px 12px', fontSize: '0.875rem' },
  md: { padding: '10px 20px', fontSize: '1rem' },
  lg: { padding: '14px 28px', fontSize: '1.125rem' },
};

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled,
  children,
  style,
  ...props
}) => {
  const baseStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    borderRadius: '8px',
    fontWeight: 500,
    cursor: disabled || loading ? 'not-allowed' : 'pointer',
    opacity: disabled || loading ? 0.6 : 1,
    transition: 'all 0.2s ease',
    ...variantStyles[variant],
    ...sizeStyles[size],
    ...style,
  };

  return (
    <button style={baseStyle} disabled={disabled || loading} {...props}>
      {loading && <Spinner size="sm" />}
      {children}
    </button>
  );
};

const Spinner: React.FC<{ size?: 'sm' | 'md' }> = ({ size = 'sm' }) => {
  const dimension = size === 'sm' ? 14 : 20;
  return (
    <svg
      width={dimension}
      height={dimension}
      viewBox="0 0 24 24"
      fill="none"
      style={{ animation: 'spin 1s linear infinite' }}
    >
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        strokeDasharray="32"
        strokeDashoffset="12"
      />
    </svg>
  );
};
