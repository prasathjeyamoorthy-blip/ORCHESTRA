# index.css - Global Styles

## Purpose
Global CSS stylesheet defining base styles, design tokens, typography, and component utilities used throughout the application.

## Core Styling Sections

### CSS Variables (Design Tokens)
```css
:root {
  /* Colors */
  --primary: #007bff;
  --secondary: #6c757d;
  --success: #28a745;
  --danger: #dc3545;
  --warning: #ffc107;
  --info: #17a2b8;
  
  /* Spacing */
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;
  
  /* Typography */
  --font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.25rem;
  --font-size-xl: 1.5rem;
  
  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);
}
```

### Base Elements
```css
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
  height: 100%;
}

body {
  font-family: var(--font-family);
  font-size: var(--font-size-base);
  line-height: 1.5;
  color: #333;
  background-color: #fff;
}
```

### Typography

#### Headings
```css
h1, h2, h3, h4, h5, h6 {
  font-weight: 600;
  line-height: 1.2;
  margin-bottom: var(--spacing-md);
}

h1 { font-size: var(--font-size-xl); }
h2 { font-size: 1.75rem; }
h3 { font-size: 1.5rem; }
```

#### Text Utilities
```css
.text-center { text-align: center; }
.text-right { text-align: right; }
.text-left { text-align: left; }

.text-muted { color: #6c757d; }
.text-danger { color: #dc3545; }
.text-success { color: #28a745; }

.font-bold { font-weight: 700; }
.font-semibold { font-weight: 600; }
.font-normal { font-weight: 400; }
```

### Layout Utilities

#### Display
```css
.d-flex { display: flex; }
.d-grid { display: grid; }
.d-block { display: block; }
.d-inline { display: inline; }
.d-inline-block { display: inline-block; }

.flex-row { flex-direction: row; }
.flex-col { flex-direction: column; }
.justify-center { justify-content: center; }
.items-center { align-items: center; }
```

#### Spacing
```css
.m-0 { margin: 0; }
.m-1 { margin: var(--spacing-md); }
.mx-auto { margin-left: auto; margin-right: auto; }

.p-2 { padding: var(--spacing-lg); }
.px-3 { padding-left: var(--spacing-xl); padding-right: var(--spacing-xl); }
```

### Color Classes

#### Background Colors
```css
.bg-primary { background-color: var(--primary); }
.bg-secondary { background-color: var(--secondary); }
.bg-success { background-color: var(--success); }
.bg-danger { background-color: var(--danger); }
.bg-light { background-color: #f8f9fa; }
.bg-dark { background-color: #343a40; }
```

#### Text Colors
```css
.text-primary { color: var(--primary); }
.text-secondary { color: var(--secondary); }
.text-success { color: var(--success); }
```

### Component Styles

#### Buttons
```css
.btn {
  padding: var(--spacing-md) var(--spacing-lg);
  border: none;
  border-radius: 0.25rem;
  font-size: var(--font-size-base);
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-primary {
  background-color: var(--primary);
  color: white;
}

.btn-primary:hover {
  background-color: #0056b3;
  box-shadow: var(--shadow-md);
}

.btn-disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
```

#### Forms
```css
input, textarea, select {
  width: 100%;
  padding: var(--spacing-md);
  border: 1px solid #ddd;
  border-radius: 0.25rem;
  font-size: var(--font-size-base);
  font-family: inherit;
}

input:focus, textarea:focus, select:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.25);
}

.form-group {
  margin-bottom: var(--spacing-lg);
}

label {
  display: block;
  margin-bottom: var(--spacing-sm);
  font-weight: 600;
}
```

#### Cards
```css
.card {
  background-color: white;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  padding: var(--spacing-lg);
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.3s ease;
}

.card:hover {
  box-shadow: var(--shadow-md);
}

.card-header {
  padding: var(--spacing-lg);
  border-bottom: 1px solid #ddd;
  font-weight: 600;
}

.card-body {
  padding: var(--spacing-lg);
}

.card-footer {
  padding: var(--spacing-lg);
  border-top: 1px solid #ddd;
  background-color: #f8f9fa;
}
```

### Responsive Grid
```css
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--spacing-lg);
}

.row {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: var(--spacing-md);
}

.col { grid-column: span 1; }
.col-6 { grid-column: span 6; }
.col-12 { grid-column: span 12; }

@media (max-width: 768px) {
  .col-md-6 { grid-column: span 12; }
}
```

### Animations
```css
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.fade-in { animation: fadeIn 0.3s ease; }
.slide-up { animation: slideUp 0.3s ease; }
```

### Dark Mode Support
```css
@media (prefers-color-scheme: dark) {
  :root {
    --bg-primary: #1a1a1a;
    --bg-secondary: #2d2d2d;
    --text-primary: #fff;
    --text-secondary: #ccc;
  }
}
```

### Print Styles
```css
@media print {
  body {
    font-size: 12pt;
    color: black;
  }
  .no-print {
    display: none;
  }
}
```

## Utility Classes Reference

### Common Utilities
- `.m-*` / `.p-*` - Margin / Padding
- `.text-*` - Text alignment and color
- `.bg-*` - Background color
- `.flex-*` - Flexbox utilities
- `.rounded` - Border radius
- `.shadow-*` - Box shadows
- `.opacity-*` - Opacity levels

## Responsive Design

### Breakpoints
```css
/* Mobile First Approach */
/* Mobile: 0 - 640px */
/* Tablet: 640px - 1024px */
/* Desktop: 1024px+ */

@media (min-width: 640px) { /* Tablet */ }
@media (min-width: 1024px) { /* Desktop */ }
```

## Accessibility

### Focus States
```css
:focus {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

button:focus-visible {
  outline: 2px solid var(--primary);
}
```

### Reduced Motion
```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

## CSS Preprocessor (if using SCSS/SASS)

### Variables
```scss
$primary-color: #007bff;
$spacing-unit: 1rem;

@mixin button-base {
  padding: $spacing-unit;
  border: none;
  cursor: pointer;
}
```

## Performance Optimization
- Minimal specificity (BEM naming)
- No !important declarations
- Efficient selectors
- Critical CSS inlined
- Non-critical CSS deferred

## Browser Compatibility
- All modern browsers
- CSS Grid support
- Flexbox support
- CSS Variables support
- Media query support

## Notes
- Uses CSS custom properties for theming
- Follows mobile-first approach
- Supports light and dark modes
- Accessible color contrasts
- Print-friendly styles included
