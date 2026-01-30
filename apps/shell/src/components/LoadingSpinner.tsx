import React from 'react';

interface LoadingSpinnerProps {
  message?: string;
  size?: 'small' | 'medium' | 'large';
  fullScreen?: boolean;
}

/**
 * Loading Spinner Component
 * Displays a loading indicator with optional message
 */
const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  message = 'Loading...',
  size = 'medium',
  fullScreen = false,
}) => {
  const sizeMap = {
    small: 24,
    medium: 40,
    large: 60,
  };

  const spinnerSize = sizeMap[size];

  const containerClass = fullScreen
    ? 'loading-spinner-container loading-spinner-fullscreen'
    : 'loading-spinner-container';

  return (
    <div className={containerClass} role="status" aria-live="polite">
      <svg
        className="loading-spinner"
        width={spinnerSize}
        height={spinnerSize}
        viewBox="0 0 50 50"
        aria-hidden="true"
      >
        <circle
          className="spinner-track"
          cx="25"
          cy="25"
          r="20"
          fill="none"
          strokeWidth="4"
        />
        <circle
          className="spinner-head"
          cx="25"
          cy="25"
          r="20"
          fill="none"
          strokeWidth="4"
          strokeLinecap="round"
        />
      </svg>
      {message && <p className="loading-message">{message}</p>}
      <span className="sr-only">{message}</span>
    </div>
  );
};

export default LoadingSpinner;
