import React from 'react';

interface ModuleInfoProps {
  moduleName: string;
  agGridVersion: string;
  description: string;
}

/**
 * Displays module information including AG Grid version
 * Useful for debugging and demonstrating module isolation
 */
const ModuleInfo: React.FC<ModuleInfoProps> = ({
  moduleName,
  agGridVersion,
  description,
}) => {
  return (
    <div className="module-info">
      <div className="module-info-header">
        <h2>{moduleName}</h2>
        <span className="version-badge">AG Grid v{agGridVersion}</span>
      </div>
      <p className="module-description">{description}</p>
    </div>
  );
};

export default ModuleInfo;
