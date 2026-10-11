import type { Metadata } from "next";
import { InstagramPage } from "@/components/manager/instagram";

export const metadata: Metadata = { title: "Instagram" };

export default function Page() {
  return <InstagramPage />;
}
