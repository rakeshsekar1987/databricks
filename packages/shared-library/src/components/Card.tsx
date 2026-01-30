import React from 'react';

export interface CardProps {
  title?: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  variant?: 'default' | 'elevated' | 'outlined';
  padding?: 'sm' | 'md' | 'lg';
}

const paddingStyles: Record<string, string> = {
  sm: '12px',
  md: '20px',
  lg: '28px',
};

export const Card: React.FC<CardProps> = ({
  title,
  subtitle,
  children,
  footer,
  variant = 'default',
  padding = 'md',
}) => {
  const baseStyle: React.CSSProperties = {
    background: 'white',
    borderRadius: '12px',
    overflow: 'hidden',
    ...(variant === 'elevated' && {
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    }),
    ...(variant === 'outlined' && {
      border: '1px solid #e2e8f0',
    }),
    ...(variant === 'default' && {
      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
    }),
  };

  return (
    <div style={baseStyle}>
      {(title || subtitle) && (
        <div style={{ padding: paddingStyles[padding], borderBottom: '1px solid #e2e8f0' }}>
          {title && (
            <h3 style={{ margin: 0, fontSize: '1.125rem', fontWeight: 600, color: '#2d3748' }}>
              {title}
            </h3>
          )}
          {subtitle && (
            <p style={{ margin: '4px 0 0', fontSize: '0.875rem', color: '#718096' }}>
              {subtitle}
            </p>
          )}
        </div>
      )}
      <div style={{ padding: paddingStyles[padding] }}>{children}</div>
      {footer && (
        <div
          style={{
            padding: paddingStyles[padding],
            borderTop: '1px solid #e2e8f0',
            background: '#f7fafc',
          }}
        >
          {footer}
        </div>
      )}
    </div>
  );
};
