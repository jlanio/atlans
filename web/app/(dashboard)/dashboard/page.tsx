import DashboardView from "@/app/components/dashboard"

// Thin wrapper: the scope, the data and the composition live in `DashboardView`
// (docs/specs/dashboard.md §3.2). The page only mounts the route.
export default function DashboardPage() {
  return <DashboardView />
}
