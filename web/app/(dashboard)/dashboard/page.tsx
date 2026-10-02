import DashboardView from "@/app/components/dashboard"

// Wrapper fino: o escopo, os dados e a composição vivem no `DashboardView`
// (docs/specs/dashboard.md §3.2). A página só monta a rota.
export default function DashboardPage() {
  return <DashboardView />
}
