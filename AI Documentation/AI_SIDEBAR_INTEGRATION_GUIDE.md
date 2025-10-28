# AI Assistant Sidebar Integration Guide

## Overview

The AI Assistant has been redesigned as a **sidebar** that slides in from the right side, with **role-based access control** - only **Senior_admins** can see and use it.

## Files Created

1. **`fe/src/AIComponents/ChatSidebar.jsx`** - Main sidebar component
2. **`fe/src/css/ChatSidebar.css`** - Sidebar styles
3. **`fe/src/AIComponents/AIAssistant.jsx`** - Wrapper with role checking

## Integration Options

### Option 1: Add to Main Navigation/Sidebar (Recommended)

If you have a left sidebar or navigation menu, add the AI Assistant button there:

**Example for a sidebar component:**

```jsx
// In your Sidebar.jsx or Navigation.jsx
import AIAssistant from './AIComponents/AIAssistant';

function Sidebar({ currentProject }) {
  return (
    <div className="sidebar">
      {/* Your existing navigation items */}
      <NavLink to="/projects">Projects</NavLink>
      <NavLink to="/inventory">Inventory</NavLink>
      <NavLink to="/sites">Sites</NavLink>

      {/* Add AI Assistant - only shows for Senior_admins */}
      <div className="nav-section">
        <AIAssistant
          projectContext={currentProject ? {
            type: currentProject.type,
            id: currentProject.id
          } : null}
        />
      </div>
    </div>
  );
}
```

### Option 2: Add to Top Navigation Bar

**Example for a header/navbar:**

```jsx
// In your Header.jsx or Navbar.jsx
import AIAssistant from './AIComponents/AIAssistant';

function Header({ user, currentProject }) {
  return (
    <header className="app-header">
      <div className="header-left">
        <Logo />
        <h1>BOQ Management</h1>
      </div>

      <div className="header-right">
        {/* Other header items */}
        <Notifications />

        {/* AI Assistant button - only shows for Senior_admins */}
        <AIAssistant projectContext={currentProject} />

        <UserMenu user={user} />
      </div>
    </header>
  );
}
```

### Option 3: Add to Project-Specific Pages

**Example for Project.jsx:**

```jsx
// In fe/src/Components/Project.jsx
import AIAssistant from '../AIComponents/AIAssistant';

function Project() {
  const [currentProject, setCurrentProject] = useState(null);

  return (
    <div className="project-page">
      <div className="project-header">
        <h2>Project Management</h2>

        {/* AI Assistant button - context-aware */}
        {currentProject && (
          <AIAssistant
            projectContext={{
              type: 'boq',
              id: currentProject.id
            }}
          />
        )}
      </div>

      {/* Rest of your project component */}
    </div>
  );
}
```

### Option 4: Global Integration in App.jsx

**Simplest approach - always available:**

```jsx
// In fe/src/App.jsx
import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import AIAssistant from './AIComponents/AIAssistant';

function App() {
  const [currentProject, setCurrentProject] = useState(null);

  return (
    <BrowserRouter>
      <div className="App">
        {/* Your existing routes and components */}
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/projects" element={<Projects />} />
          {/* ... other routes */}
        </Routes>

        {/* AI Assistant - globally available, only shows for Senior_admins */}
        <AIAssistant projectContext={currentProject} />
      </div>
    </BrowserRouter>
  );
}
```

## Role-Based Access Control

The `AIAssistant` component automatically checks the user's role:

### How it works:

1. **Checks localStorage** for user data
2. If not found, **fetches from API** (endpoint: `/me`)
3. **Verifies role** is `senior_admin`
4. If **not authorized**, component returns `null` (invisible)
5. If **authorized**, shows the AI Assistant button

### User Data Format Expected:

```javascript
// In localStorage as 'user' or from API /me
{
  "id": 1,
  "username": "john_doe",
  "role": "senior_admin",  // or role: { role_name: "senior_admin" }
  // ... other user fields
}
```

### Supported Role Formats:

```javascript
// Format 1: Direct string
{ role: "senior_admin" }

// Format 2: Object with role_name
{ role: { role_name: "senior_admin" } }

// Format 3: Case-insensitive
{ role: "Senior_Admin" }  // Works!
{ role: "SENIOR_ADMIN" }  // Works!
```

## Updating User Role Check Logic

If your app stores user data differently, modify `AIAssistant.jsx`:

```jsx
const checkUserRole = async () => {
  try {
    // Option A: Get from your auth context
    const user = useContext(AuthContext).user;
    setUserRole(user.role);

    // Option B: Get from Redux store
    const user = useSelector(state => state.auth.user);
    setUserRole(user.role);

    // Option C: Get from your custom API endpoint
    const response = await api.get('/api/current-user');
    setUserRole(response.data.role_name);

  } catch (error) {
    console.error('Error checking user role:', error);
    setUserRole(null);
  } finally {
    setIsLoading(false);
  }
};
```

## Styling the Toggle Button

### Default Style
The button comes with a purple gradient style. It's fully styled by default.

### Custom Styling for Navigation
If integrating into existing nav, add a className:

```jsx
<AIAssistant
  projectContext={projectContext}
  className="nav-item"  // Apply your nav item styles
/>
```

Then update the component to accept className:

```jsx
// In AIAssistant.jsx
const AIAssistant = ({ projectContext = null, className = '' }) => {
  return (
    <button
      className={`ai-assistant-toggle ${className}`}
      onClick={() => setIsSidebarOpen(!isSidebarOpen)}
    >
      <Bot size={20} />
      <span>AI Assistant</span>
    </button>
  );
};
```

## Project Context

The `projectContext` prop tells the AI which project the user is viewing:

```jsx
// No context (general chat)
<AIAssistant />

// With context (project-aware)
<AIAssistant
  projectContext={{
    type: 'boq',    // 'boq', 'ran', or 'rop'
    id: 123         // Project ID
  }}
/>
```

### Example: Dynamic Context from URL

```jsx
import { useParams } from 'react-router-dom';

function ProjectPage() {
  const { projectId } = useParams();

  return (
    <div>
      <AIAssistant
        projectContext={{
          type: 'boq',
          id: parseInt(projectId)
        }}
      />
      {/* Rest of page */}
    </div>
  );
}
```

## Features

### 1. Chat Tab
- Natural language conversation
- Function calling (create projects, search, etc.)
- Quick action buttons
- Message history
- Action confirmations
- Source citations for document answers

### 2. Documents Tab
- Placeholder for document management
- Can be expanded to show uploaded docs
- Switch back to chat easily

## Testing

### 1. Test Role Access

**As Senior_admin:**
```
1. Login as senior_admin
2. Navigate to any page
3. See "AI Assistant" button
4. Click to open sidebar
5. Chat should work
```

**As Regular User:**
```
1. Login as user/admin/viewer
2. Navigate to same page
3. AI Assistant button should NOT appear
```

### 2. Test Context Awareness

```
1. Open a BOQ project
2. Open AI Assistant
3. See "BOQ #123" in header
4. Ask: "Summarize this project"
5. AI should know the context
```

### 3. Test Sidebar Interaction

```
1. Open sidebar
2. Send message
3. Receive response
4. Try quick actions
5. Close sidebar with X
6. Re-open and history persists
```

## Advanced Customization

### Multiple Roles

To allow more roles, modify the `canAccessAI()` function:

```jsx
const canAccessAI = () => {
  if (!userRole) return false;

  const roleStr = typeof userRole === 'string'
    ? userRole.toLowerCase()
    : userRole.role_name?.toLowerCase();

  // Allow multiple roles
  const allowedRoles = ['senior_admin', 'admin'];
  return allowedRoles.includes(roleStr);
};
```

### Feature Flags

Add feature flag checking:

```jsx
const canAccessAI = () => {
  if (!userRole) return false;

  // Check role
  const isSeniorAdmin = roleStr === 'senior_admin';

  // Check feature flag
  const featureEnabled = localStorage.getItem('ai_enabled') === 'true';

  return isSeniorAdmin && featureEnabled;
};
```

### Custom Icon

Change the icon:

```jsx
import { Sparkles } from 'react-icons/fi';  // Different icon

<button className="ai-assistant-toggle">
  <Sparkles size={20} />
  <span>AI Helper</span>
</button>
```

## Mobile Responsiveness

The sidebar automatically adapts to mobile:
- On desktop: 400px width sidebar
- On mobile: Full-screen overlay

## Performance

- Role check happens once on mount
- Sidebar renders only when open
- Messages lazy-load
- Chat history cached in component state

## Security Notes

1. **Client-side role check** - For UI only
2. **Backend still validates** - All API calls require JWT
3. **Role enforcement** - Backend checks permissions on every request
4. **Audit logging** - All AI actions logged in database

## Troubleshooting

### Button Doesn't Appear

**Cause:** Not logged in as senior_admin

**Solution:**
```sql
-- Check user role in database
SELECT u.username, r.role_name
FROM users u
JOIN roles r ON u.role_id = r.id
WHERE u.username = 'your_username';

-- Update role if needed
UPDATE users
SET role_id = (SELECT id FROM roles WHERE role_name = 'senior_admin')
WHERE username = 'your_username';
```

### Button Appears but Sidebar Doesn't Open

**Check browser console** for errors. Common issues:
- Missing CSS file import
- React icon import error
- API connection issue

### Role Check Fails

Add debug logging:

```jsx
const checkUserRole = async () => {
  try {
    const storedUser = localStorage.getItem('user');
    console.log('Stored user:', storedUser);

    if (storedUser) {
      const user = JSON.parse(storedUser);
      console.log('Parsed user:', user);
      console.log('Role:', user.role);
      setUserRole(user.role);
    }
  } catch (error) {
    console.error('Role check error:', error);
  }
};
```

## Example: Complete Integration

```jsx
// Complete example in a typical app structure

// App.jsx
import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Routes from './routes';
import AIAssistant from './AIComponents/AIAssistant';

function App() {
  const [currentProject, setCurrentProject] = useState(null);

  return (
    <div className="app">
      <Header />
      <div className="app-body">
        <Sidebar />
        <main className="app-content">
          <Routes onProjectChange={setCurrentProject} />
        </main>
      </div>

      {/* AI Assistant - globally available */}
      <AIAssistant projectContext={currentProject} />
    </div>
  );
}

export default App;
```

## Next Steps

1. Choose integration option (nav, header, or global)
2. Add `<AIAssistant />` to your chosen location
3. Pass `projectContext` if on project pages
4. Test with senior_admin account
5. Verify regular users can't see it
6. Customize styling as needed

---

**Documentation:**
- User Guide: [AI_INTEGRATION_README.md](AI_INTEGRATION_README.md)
- API Docs: [API endpoints](AI_INTEGRATION_README.md#api-endpoints)
- Troubleshooting: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

**Ready to integrate!** The sidebar is production-ready and fully functional for Senior_admins only.
