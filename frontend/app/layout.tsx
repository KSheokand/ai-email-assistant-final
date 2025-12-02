// app/layout.tsx
import "./globals.css";

export const metadata = {
  title: "AI Email Assistant",
  description: "Chatbot dashboard for Gmail automation",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-slate-950 text-slate-100">{children}</body>
    </html>
  );
}
