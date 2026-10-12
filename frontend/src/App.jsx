import React, { useState, useEffect } from 'react';
import { ScreeningProvider, useScreening } from './context/ScreeningContext';
import { AppShell } from './components/layout/AppShell';
import { JobIntake } from './components/intake/JobIntake';
import { RubricEditor } from './components/intake/RubricEditor';
import { ResumeDropzone } from './components/upload/ResumeDropzone';
import { EvaluationView } from './components/screening/EvaluationView';
import { ComparisonMatrix } from './components/screening/ComparisonMatrix';
import { NotFoundPage } from './components/common/NotFoundPage';
import { ErrorBoundary } from './components/common/ErrorBoundary';

function ScreeningContent({ currentPath, onNavigateHome }) {
  const { activeStep, isScreening } = useScreening();

  // If path is not root '/' and not an allowed route, show 404
  const isKnownRoute =
    currentPath === '/' ||
    currentPath === '' ||
    currentPath === '/index.html' ||
    currentPath === '/screening' ||
    currentPath === '/results';

  if (!isKnownRoute) {
    return <NotFoundPage onNavigateHome={onNavigateHome} />;
  }

  // If screening execution is active, render Stage 4 EvaluationView
  if (isScreening || activeStep === 'evaluation') {
    return <EvaluationView />;
  }

  return (
    <>
      {(activeStep === 'job' || activeStep === 'intake') && <JobIntake />}
      {activeStep === 'requirements' && <RubricEditor />}
      {(activeStep === 'resumes' || activeStep === 'upload') && <ResumeDropzone />}
      {activeStep === 'results' && <ComparisonMatrix />}
    </>
  );
}

export default function App() {
  const [currentPath, setCurrentPath] = useState(
    typeof window !== 'undefined' ? window.location.pathname : '/'
  );

  useEffect(() => {
    // Keep document title strictly VectorHire
    document.title = 'VectorHire';

    const handleLocationChange = () => {
      setCurrentPath(window.location.pathname);
      document.title = 'VectorHire';
    };

    window.addEventListener('popstate', handleLocationChange);
    return () => window.removeEventListener('popstate', handleLocationChange);
  }, []);

  const handleNavigateHome = () => {
    if (typeof window !== 'undefined' && window.history) {
      window.history.pushState({}, '', '/');
      setCurrentPath('/');
      document.title = 'VectorHire';
    }
  };

  return (
    <ErrorBoundary>
      <ScreeningProvider>
        <AppShell>
          <ScreeningContent
            currentPath={currentPath}
            onNavigateHome={handleNavigateHome}
          />
        </AppShell>
      </ScreeningProvider>
    </ErrorBoundary>
  );
}
