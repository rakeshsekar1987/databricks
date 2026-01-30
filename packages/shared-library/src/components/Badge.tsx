import React from 'react';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  size?: 'sm' | 'md';
}

const variantStyles: Record<string, { background: string; color: string }> = {
  default: { background: '#e2e8f0', color: '#4a5568' },
  success: { background: '#c6f6d5', color: '#276749' },
  warning: { background: '#feebc8', color: '#c05621' },
  danger: { background: '#fed7d7', color: '#c53030' },
  info: { background: '#bee3f8', color: '#2b6cb0' },
};

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'md',
}) => {
  const { background, color } = variantStyles[variant];
  
  const style: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    padding: size === 'sm' ? '2px 8px' : '4px 12px',
    fontSize: size === 'sm' ? '0.75rem' : '0.875rem',
    fontWeight: 500,
    borderRadius: '20px',
    background,
    color,
  };

  return <span style={style}>{children}</span>;
};
