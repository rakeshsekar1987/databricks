import React from 'react';

interface ModuleInfoProps {
  moduleName: string;
  agGridVersion: string;
  description: string;
}

const ModuleInfo: React.FC<ModuleInfoProps> = ({ moduleName, agGridVersion, description }) => (
  <div className="module-info">
    <div className="module-info-header">
      <h2>{moduleName}</h2>
      <span className="version-badge">AG Grid v{agGridVersion}</span>
    </div>
    <p className="module-description">{description}</p>
  </div>
);

export default ModuleInfo;
