# IntelliStock Frontend - Lovable.dev Prompt

## System Context

You are building the frontend for **IntelliStock Agent**, an AI-powered shelf inventory monitoring system. The backend is fully functional with 33+ REST endpoints running on `http://localhost:8000/api/v1`.

---

## Product Overview

**IntelliStock Agent** uses computer vision + AI to provide real-time, trusted inventory state for retail shelves.

**Key Users:**
- Store managers (overview, alerts)
- Inventory staff (restocking, audit)
- Operations (real-time monitoring)

**Core Features:**
- Live inventory dashboard with KPIs
- Zone-based inventory filtering
- Real-time alerts (low stock, camera offline)
- Activity feed (recent reconciliations)
- Camera status monitoring
- AI-powered insights and anomaly detection

---

## Design Requirements

### Visual Style
- **Modern, minimal, professional**
- **Dark theme primary** (light mode toggle)
- **Real-time feel** (live indicators, smooth animations)
- **High contrast** (accessibility WCAG AA)
- **Production-grade** (not a prototype)

### Layout & Navigation
1. **Sidebar Navigation** (always visible, collapsible on mobile)
   - Logo + company name
   - Main nav items with icons
   - User profile menu at bottom
   - Dark/light theme toggle

2. **Main Content Area**
   - Responsive grid layout
   - Breadcrumbs for context
   - Action buttons (top right)
   - Footer with status indicators

3. **Mobile Responsive**
   - Works on phones, tablets, desktops
   - Sidebar collapses on mobile
   - Touch-friendly interactions
   - Optimized metric cards

---

## Page Specifications

### 1. Dashboard (Home)
**Purpose:** At-a-glance view of entire operation

**Content:**
- **Top KPI Cards (4 columns, responsive):**
  - Total SKUs tracked (with trending icon)
  - Active cameras / Total cameras
  - Low stock alerts (red badge if > 0)
  - Avg reconciliation confidence %
  - Click cards to drill down to detail pages

- **Zone Health Grid (4x4 grid, responsive)**
  - 16 zone cards showing:
    - Zone ID (e.g., "A-1")
    - Zone label (e.g., "Beverages · Water & Soda")
    - Health indicator (healthy=green, low=yellow, offline=red, pending=blue)
    - Confidence % (e.g., "97%")
    - Live indicator (blinking dot if active)
  - Hover: Show camera name + last update time
  - Click: Go to zone inventory

- **Activity Feed (right sidebar or bottom)**
  - Recent verified reconciliations
  - Timestamp relative format (e.g., "2m ago")
  - Show: Zone, Product, Quantity change (from → to)
  - Confidence badge
  - Auto-scroll on new events

- **Live Indicators**
  - "LIVE" badge in top-right (pulsing green)
  - WebSocket connection status
  - Last update timestamp

### 2. Inventory Page
**Purpose:** Detailed product view with filtering

**Content:**
- **Filter Bar (top)**
  - Zone dropdown (16 zones + "All")
  - Category dropdown (Beverages, Snacks, Dry, Dairy, Household, Personal)
  - Status filter (Adequate, Low Stock, Out of Stock)
  - Search by SKU or product name
  - Clear filters button

- **Product Table (or card grid)**
  - Columns: SKU, Product Name, Zone, Verified Qty, Observed Qty, Threshold, Status, Confidence, Actions
  - Status color-coded (adequate=green, low=yellow, out=red)
  - Sortable columns
  - Pagination (50 per page default)
  - Bulk actions (mark reviewed, export)

- **Bulk Actions Modal**
  - Mark as reviewed
  - Export to CSV
  - Print label
  - Restock notification

### 3. Alerts Page
**Purpose:** Manage and act on alerts

**Content:**
- **Alert Filters (top)**
  - Severity (Critical, Warning, Info)
  - Type (Low Stock, Camera Offline, Anomaly)
  - Status (Unacknowledged, Acknowledged, Resolved)
  - Date range picker

- **Alert List/Cards**
  - Alert title with severity icon
  - Detail text + zone
  - Time since alert
  - Actions: Acknowledge, Dismiss, View Details

- **Alert Details Modal**
  - Full context
  - Suggested action
  - History of similar alerts
  - Acknowledge + note field

- **Bulk Actions**
  - Acknowledge all
  - Acknowledge by severity
  - Export report

### 4. Shelves/Cameras Page
**Purpose:** Monitor camera health and coverage

**Content:**
- **Camera Grid (2-3 columns)**
  - Camera card showing:
    - Camera name + location
    - Live feed placeholder (gray box with icon)
    - Online/Offline status (green/red)
    - Zones covered (list or chips)
    - Last heartbeat time
    - Frame rate (fps)
    - Actions: Configure, Test, View Live

- **Zone-to-Camera Map**
  - Table showing: Zone → Camera → Health
  - Highlight offline cameras
  - Show zones without coverage

- **Camera Configuration Modal**
  - Camera name
  - Location
  - RTSP/HTTP source URL
  - Frame rate
  - Confidence threshold
  - ROI polygon editor (visual)

### 5. Insights Page (AI Agents)
**Purpose:** AI-powered recommendations

**Content:**
- **Tabs:** Recommendations | Anomalies | Trends

- **Recommendations Tab**
  - Cards showing:
    - "Restock Product X in Zone Y"
    - Reason (e.g., "Below threshold, fast depletion trend")
    - Confidence score
    - Suggested action + "Accept/Dismiss" buttons

- **Anomalies Tab**
  - Flagged items with anomaly type
  - Sudden drop icon
  - Count discrepancy alerts
  - Confidence anomalies
  - Action: "Review" or "False Alarm"

- **Trends Tab**
  - Mini chart (12-hour, 7-day options)
  - Top selling products
  - Fastest depleting items
  - Stock replenishment efficiency

### 6. Settings Page
**Purpose:** Configuration and profile

**Content:**
- **Tabs:** General | Notifications | Security | About

- **General Tab**
  - Store name + location
  - Operating hours
  - Theme selector (dark/light)
  - Language selector

- **Notifications Tab**
  - Alert preferences by severity
  - Email notifications toggle
  - SMS notifications toggle
  - Quiet hours (do not disturb)

- **Security Tab**
  - Change password
  - Two-factor authentication
  - API keys (view/regenerate)
  - Session history

- **About Tab**
  - Version number
  - Backend status
  - Database connection status
  - Support info + links

---

## Component Library

### Design System
- **Colors:**
  - Primary: Blue (#3B82F6)
  - Success/Healthy: Green (#10B981)
  - Warning/Low: Amber (#F59E0B)
  - Critical/Offline: Red (#EF4444)
  - Info: Cyan (#06B6D4)
  - Background: Dark gray (#0F172A) for dark mode
  - Text: White (#F8FAFC) for dark mode

- **Typography:**
  - Headers: Geist Sans (or Inter)
  - Body: Geist Sans (or Inter)
  - Mono: JetBrains Mono (for SKUs, codes)

- **Spacing:** 4px base unit (4, 8, 12, 16, 24, 32, 48, 64px)

- **Border Radius:** 8px default, 4px compact

- **Shadows:** Subtle, dark-appropriate

### Reusable Components
- **Header** (with logo, search, profile, notifications)
- **Sidebar** (collapsible, with active state)
- **KPI Card** (metric, trend, sparkline)
- **Zone Card** (health indicator, confidence)
- **Alert Badge** (severity color)
- **Status Dot** (healthy/low/offline/pending)
- **Data Table** (sortable, paginated, selectable rows)
- **Modal** (alerts, confirmations, forms)
- **Toast Notifications** (top-right corner)
- **Loading Skeleton** (while fetching)
- **Empty State** (when no data)

---

## API Integration

### Backend Base URL
```
http://localhost:8000/api/v1
```

### Key Endpoints to Consume

**Dashboard:**
- `GET /dashboard/metrics` → KPI cards
- `GET /dashboard/store-info` → Store metadata

**Zones:**
- `GET /zones` → Zone grid

**Inventory:**
- `GET /inventory?zone_id=...&status=...` → Product table

**Alerts:**
- `GET /alerts?acknowledged=false` → Alert list
- `POST /alerts/{id}/acknowledge` → Mark acknowledged

**Events:**
- `GET /events?limit=30` → Activity feed

**Agents (Insights):**
- `GET /agents/runs` → AI agent history
- `GET /agents/stats` → Performance metrics

**WebSocket:**
- `WS /ws` → Real-time updates
- Messages: `inventory_update`, `alert_created`, `agent_event`

### Error Handling
- Graceful 404, 500 handling
- Retry logic on network errors
- Show user-friendly error messages
- Log errors to console in dev

### Loading & Caching
- Show loading skeletons while fetching
- Cache dashboard metrics for 30s
- Real-time updates via WebSocket
- Fallback to mock data if API unavailable

---

## Advanced Features

### Real-Time Updates
- **WebSocket Connection**
  - Show connection status (top-right)
  - Auto-reconnect on disconnect
  - Show "LIVE" badge when connected

- **Activity Feed**
  - New events slide in from top
  - Animate when new alert appears
  - Auto-update KPI cards

### User Experience
- **Keyboard Shortcuts**
  - Cmd/Ctrl+K for command palette (search)
  - Cmd/Ctrl+Shift+D for dashboard
  - Cmd/Ctrl+Shift+A for alerts
  - ? for help

- **Accessibility**
  - ARIA labels on all interactive elements
  - Keyboard navigation (Tab through items)
  - Color not sole indicator
  - Sufficient contrast (WCAG AA)

- **Responsive Design**
  - Mobile: Single column, stacked cards
  - Tablet: 2-column layout
  - Desktop: Full 4-column grid
  - Sidebar hidden on mobile (hamburger menu)

---

## Performance Requirements

- **Page Load:** < 3 seconds
- **Time to Interactive:** < 5 seconds
- **API Calls:** Cached where appropriate
- **Image Optimization:** WebP + lazy loading
- **Bundle Size:** < 500KB (gzipped)

---

## Tech Stack (Recommended)

- **Framework:** React 19
- **Build:** Vite
- **Router:** TanStack Router
- **State:** TanStack Query + React Context
- **UI Components:** shadcn/ui or Radix UI
- **Styling:** Tailwind CSS
- **Charts:** Recharts or Chart.js
- **Real-time:** Native WebSocket
- **Forms:** React Hook Form + Zod

---

## Success Criteria

✅ All pages implemented and functional
✅ Real-time updates working
✅ Mobile responsive (tested on devices)
✅ Accessibility compliant (keyboard nav, color contrast)
✅ Performance optimized (< 3s load time)
✅ Zero console errors in production
✅ Graceful error handling
✅ Beautiful, professional UI
✅ Easy to use and intuitive
✅ Ready for FYP presentation
