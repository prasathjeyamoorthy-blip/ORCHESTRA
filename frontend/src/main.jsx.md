# main.jsx - Application Entry Point

## Purpose
Bootstrap script that initializes the React application. Mounts the App component to the DOM and configures global settings.

## Key Responsibilities
- Initialize React application
- Mount to DOM element
- Configure providers
- Set up error handling
- Initialize global services

## Execution Flow

```
1. Module Load
   ↓
2. Supabase Initialization
   ↓
3. API Client Setup
   ↓
4. React Root Creation
   ↓
5. App Mounting
   ↓
6. Application Ready
```

## Configuration

### Environment Setup
```javascript
// Load environment variables
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
```

### Supabase Client
```javascript
import { createClient } from '@supabase/supabase-js';

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY
);
```

### API Client
```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 10000
});

// Add auth interceptor
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

## Global Providers

### Root Provider Setup
```javascript
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <App />
        </ThemeProvider>
      </QueryClientProvider>
    </BrowserRouter>
  </React.StrictMode>
);
```

### Provider Hierarchy
```
StrictMode (development checks)
  ├─ BrowserRouter (routing)
  ├─ QueryClientProvider (data fetching)
  ├─ ThemeProvider (theming)
  └─ App
```

## Error Handling

### Global Error Handler
```javascript
window.addEventListener('error', (event) => {
  console.error('Global error:', event.error);
  // Send to error tracking service
});

window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled promise rejection:', event.reason);
});
```

## Service Initialization

### Logger Setup
```javascript
import { initializeLogger } from './utils/logger';
initializeLogger();
```

### Analytics Setup
```javascript
import { initializeAnalytics } from './utils/analytics';
initializeAnalytics(import.meta.env.VITE_GA_ID);
```

### Service Worker (PWA)
```javascript
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js')
    .then(reg => console.log('SW registered'))
    .catch(err => console.error('SW error', err));
}
```

## Performance Monitoring

### Web Vitals
```javascript
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';

getCLS(console.log);
getFID(console.log);
getFCP(console.log);
getLCP(console.log);
getTTFB(console.log);
```

## DOM Element

### Root Element
```html
<!-- In index.html -->
<div id="root"></div>
```

### Root Styling
```css
#root {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
}
```

## Development vs Production

### Development Mode
- React DevTools enabled
- Warnings and errors verbose
- Source maps available
- HMR active

### Production Mode
- Optimized bundle
- Error logging to service
- Performance monitoring
- Analytics enabled

## Configuration Management

### Environment Variables
```
VITE_API_BASE_URL=http://localhost:5000
VITE_SUPABASE_URL=https://project.supabase.co
VITE_SUPABASE_ANON_KEY=public_key
VITE_GA_ID=tracking_id
```

### Feature Flags
```javascript
const FEATURES = {
  VOICE_ENABLED: import.meta.env.VITE_VOICE_ENABLED === 'true',
  MULTI_DOC_UPLOAD: import.meta.env.VITE_MULTI_DOC === 'true'
};
```

## Initialization Order

### Critical Path
1. Load environment variables
2. Initialize Supabase
3. Setup API client
4. Create React root
5. Mount App
6. Start listeners

### Post-Mount
1. Check authentication
2. Load user data
3. Initialize services
4. Start polling jobs
5. Enable real-time updates

## Error Recovery

### Initialization Errors
```javascript
try {
  initializeApp();
} catch (error) {
  console.error('Failed to initialize', error);
  // Show fallback UI
  document.body.innerHTML = '<p>Failed to load app</p>';
}
```

## Cleanup

### Unmounting
```javascript
// React cleanup
// Event listeners
// Timers
// Subscriptions
```

## Build Process Integration

### Vite Configuration
```javascript
// vite.config.js integration
// - Module resolution
// - Environment variable replacement
// - Asset handling
// - Optimization
```

## Browser Compatibility

### Required APIs
- ES6+ features
- Fetch API
- LocalStorage
- ServiceWorker (optional)

### Polyfills (if needed)
```javascript
import 'whatwg-fetch'; // Fetch polyfill
```

## Dependencies
- react - Core framework
- react-dom - DOM rendering
- vite - Build tool
- @supabase/supabase-js - Database client
- axios - HTTP client
- react-router-dom - Routing
- react-query - Data fetching
- zustand - State management

## Entry Point Definition

### package.json
```json
{
  "main": "src/main.jsx",
  "type": "module"
}
```

### HTML Script Tag
```html
<script type="module" src="/src/main.jsx"></script>
```

## Notes
- Executes once on application start
- Initializes all global services
- Sets up error boundaries
- Configures providers
- Handles environment setup
- Critical for application stability
