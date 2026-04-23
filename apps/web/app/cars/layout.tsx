import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Каталог моделей для пригону",
  description:
    "SEO-каталог популярних моделей для пригону авто зі США: огляди по роках, ринкові ціни та практичні рекомендації.",
  alternates: {
    canonical: "/cars"
  },
  robots: {
    index: true,
    follow: true
  }
};

export default function CarsLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
