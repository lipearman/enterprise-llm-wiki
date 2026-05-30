import { redirect } from "next/navigation";

// /landing is now the root path — redirect for backward compatibility
export default function LandingRedirect() {
  redirect("/");
}
