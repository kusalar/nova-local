import React from 'react';
import { CommandCenterPage } from './pages/CommandCenterPage';
import { ErrorBoundary } from './components/common/ErrorBoundary';

export function App() {
  return (
    <ErrorBoundary>
      <CommandCenterPage />
    </ErrorBoundary>
  );
}

export default App;
