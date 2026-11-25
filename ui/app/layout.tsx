import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "../context/ThemeContext";
import { AppShell } from "../components/AppShell";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#fafafa" },
    { media: "(prefers-color-scheme: dark)", color: "#09090b" },
  ],
  width: "device-width",
  initialScale: 1,
};

export const metadata: Metadata = {
  metadataBase: new URL("https://incidentiq.internal"),
  title: {
    default: "IncidentIQ — Autonomous AI On-Call Triage Copilot",
    template: "%s | IncidentIQ",
  },
  description:
    "IncidentIQ is an autonomous multi-agent incident triage and root cause investigation copilot. Evaluated on 8 production scenarios with 87.5% diagnostic accuracy, zero hallucinated citations, and strict human-in-the-loop approval gates.",
  keywords: [
    "SRE",
    "incident triage",
    "AI on-call assistant",
    "autonomous agents",
    "LangGraph",
    "FastMCP",
    "Prometheus metrics",
    "log clustering",
    "root cause analysis",
    "chaos engineering",
    "production observability",
    "devops copilot",
  ],
  authors: [{ name: "Mayank" }],
  creator: "IncidentIQ Systems",
  publisher: "IncidentIQ",
  applicationName: "IncidentIQ",
  generator: "Next.js",
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  openGraph: {
    title: "IncidentIQ — Autonomous AI On-Call Triage Copilot",
    description:
      "Autonomous multi-agent on-call investigation, real-time telemetry correlation, and safe human-authorized remediation.",
    url: "https://incidentiq.internal",
    siteName: "IncidentIQ Control Plane",
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "IncidentIQ — Autonomous AI On-Call Triage Copilot",
    description:
      "Autonomous multi-agent on-call investigation, real-time telemetry correlation, and safe human-authorized remediation.",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  icons: {
    icon: "/favicon.ico",
  },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "IncidentIQ",
  "applicationCategory": "DevOpsApplication",
  "operatingSystem": "Linux, Cloud, Kubernetes",
  "description":
    "Autonomous multi-agent on-call triage and root cause investigation assistant with deterministic evaluation benchmarks.",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "USD",
  },
  "featureList": [
    "Autonomous Multi-Agent Investigation",
    "LangGraph Parallel Specialist Graph",
    "Prometheus Anomaly Z-Score Analysis",
    "Untrusted Data Sanitized Log Clustering",
    "Hybrid BM25 and Semantic Runbook RAG",
    "Human-in-the-Loop Capability Token Gating",
    "Deterministic 8-Scenario Benchmark Suite",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body className="min-h-full flex flex-col">
        <ThemeProvider>
          <AppShell>{children}</AppShell>
        </ThemeProvider>
      </body>
    </html>
  );
}
