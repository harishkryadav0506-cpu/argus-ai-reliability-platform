import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './App';
import './index.css';

// --- Suppress known environmental console noise (NOT app code) ---
// Browser/AV-injected web-vitals attribution script kabhi-kabhi timer ke baad
// "Cannot read properties of undefined (reading 'startTime')" eval'd VM script
// se throw karta hai. Ye ARGUS source mein kahin nahi hai (src/, public/,
// package.json, vite.config, index.html — sab verified clean). Hum sirf isi
// exact signature ko suppress karte hain; baaki sab real errors normal dikhenge.
window.addEventListener('error', (event) => {
  const msg = event.message || '';
  const stack = (event.error && event.error.stack) || '';
  const file = (event.filename || '').split('/').pop() || '';
  const isInjectedVitalsNoise =
    msg.includes("reading 'startTime'") &&
    (stack.includes('reportAllChanges') ||
      file === '' ||
      /^VM\d+:?\d*$/.test(file) ||
      file.includes('anonymous') ||
      (event.filename || '').includes('extension'));
  if (isInjectedVitalsNoise) {
    event.preventDefault(); // console log suppress, baaki sab normal
  }
});

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
