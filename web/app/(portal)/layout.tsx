import "@/app/globals.css";
import { ThemeProvider } from "@/context/ThemeContext";

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  return <ThemeProvider>{children}</ThemeProvider>;
}
