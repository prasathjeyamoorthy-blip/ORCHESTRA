# App.jsx - Main Application Component

## Purpose
Root component of the React application. Handles routing, layout, theme management, and authentication state. Orchestrates all pages and components.

## Key Responsibilities
- Define application routes
- Manage global authentication state
- Provide layout wrapper
- Handle theme switching
- Manage global navigation

## Component Structure

```
App
  ├─ ThemeProvider
  │   └─ Router
  │       ├─ ProtectedRoute (authenticated routes)
  │       │   ├─ Dashboard
  │       │   ├─ DocumentUpload
  │       │   └─ ApplicationStatus
  │       │
  │       └─ PublicRoute (public pages)
  │           ├─ Home
  │           ├─ Login
  │           └─ Signup
  │
  └─ GlobalModals/Alerts
```

## Routes

### Public Routes
- `/` - Home page (landing)
- `/login` - User login
- `/signup` - User registration
- `/forgot-password` - Password reset

### Protected Routes (Require Authentication)
- `/dashboard` - Main dashboard
- `/upload` - Document upload
- `/status` - Application status
- `/documents` - View documents
- `/profile` - User profile

## Key Features

### Authentication Management
```javascript
const [user, setUser] = useState(null);
const [loading, setLoading] = useState(true);

// Check authentication on mount
useEffect(() => {
  checkAuthStatus();
}, []);
```

### Theme Management
```javascript
const [theme, setTheme] = useState('light');

function toggleTheme() {
  setTheme(theme === 'light' ? 'dark' : 'light');
}
```

### Protected Routes
```javascript
<ProtectedRoute path="/upload">
  <DocumentUpload />
</ProtectedRoute>
```

## State Management

### Local State
- Current user
- Authentication status
- Current theme
- Loading states

### Shared Context
- User context (via useAuth)
- Theme context
- Global notifications

## Layout Components

### Header
- Logo/branding
- Navigation menu
- User profile dropdown
- Theme toggle

### Sidebar
- Navigation links
- Collapsible sections
- Current page highlight
- Quick actions

### Main Content Area
- Page-specific content
- Dynamic routing
- Responsive layout

### Footer
- Copyright info
- Links
- Contact info

## Navigation Flow

```
Home/Landing
    ↓
Login/Signup
    ↓
Dashboard (authenticated)
    ├─ Upload Documents
    │   ├─ Extract Data
    │   ├─ Review Data
    │   └─ Confirm & Save
    │
    ├─ View Documents
    ├─ Check Status
    └─ Profile Settings
```

## Error Handling

### Global Error Boundary
- Catches component errors
- Shows error page
- Logs to monitoring service
- Allows user to go back

### API Error Handling
```javascript
try {
  const data = await api.call();
} catch (error) {
  showNotification({
    type: 'error',
    message: error.message
  });
}
```

## Mobile Responsiveness

### Breakpoints
- Mobile: < 640px
- Tablet: 640px - 1024px
- Desktop: > 1024px

### Responsive Layout
```javascript
if (isMobile) {
  return <MobileSidebar />;
} else {
  return <DesktopLayout />;
}
```

## Performance Optimizations

### Code Splitting
```javascript
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Upload = lazy(() => import('./pages/Upload'));
```

### Component Memoization
```javascript
export default memo(App);
```

### Asset Optimization
- Image lazy loading
- CSS/JS bundling
- Compression

## Global State

### Context Usage
```javascript
// User context
const { user, logout } = useAuth();

// Theme context
const { theme, toggleTheme } = useTheme();
```

## Initialization

### On App Load
1. Check authentication status
2. Restore user session
3. Load user preferences
4. Initialize theme
5. Setup API interceptors

## Integration Points

### API Client
- Base URL configuration
- Authentication header injection
- Error handling

### External Services
- Supabase for authentication
- Cloud storage
- Analytics

## Routing Libraries Used
- React Router v6
- Protected route wrappers
- Dynamic imports
- Lazy loading

## Global Features

### Notifications
- Toast messages
- Error alerts
- Success confirmations
- Loading indicators

### Modals
- Authentication modal
- Confirmation dialogs
- Error dialogs
- Help/info modals

## Accessibility

### WCAG Compliance
- Semantic HTML
- ARIA labels
- Keyboard navigation
- Color contrast

### Screen Reader Support
- Skip navigation link
- Proper heading hierarchy
- Image alt text
- Form labels

## Browser Support
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers

## Dependencies
- react - UI library
- react-router - Routing
- zustand/context - State management
- react-query - Data fetching

## Environment Variables

### Configuration
```
VITE_SUPABASE_URL
VITE_SUPABASE_ANON_KEY
VITE_API_BASE_URL
```

## Performance Metrics

### Monitoring
- Page load time
- Time to first contentful paint (FCP)
- Largest contentful paint (LCP)
- Cumulative layout shift (CLS)

## Development Features

### Hot Module Replacement (HMR)
- Fast refresh during development
- State preservation
- Error handling

### Debug Tools
- React DevTools
- Redux DevTools
- Network debugging

## Notes
- Serves as central hub for routing
- Manages authentication flow
- Provides layout structure
- Handles global error states
- Implements responsive design
