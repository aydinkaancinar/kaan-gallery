import type { Metadata } from "next";
import GalleryFooter from "@/components/GalleryFooter";
import GalleryHeader from "@/components/GalleryHeader";
import ThemeToggle from "@/components/ThemeToggle";

export const metadata: Metadata = {
  title: "Privacy policy — Aydın Kaan Çınar",
  description: "How this art portfolio and Clay Studio handle visitor information.",
  alternates: { canonical: "/privacy" },
};

export default function PrivacyPage() {
  return (
    <div className="gallery-shell">
      <ThemeToggle />
      <GalleryHeader />
      <main className="privacy-page">
        <h1>Privacy policy</h1>
        <p className="privacy-updated">Last updated November 11, 2026</p>

        <p>
          I am Aydın Kaan Çınar, based in Toronto, Ontario. I operate this art
          portfolio and Clay Studio at arts.kaancinar.com. This page explains
          how information is handled when you visit or contact me.
        </p>

        <h2>Information involved in a visit</h2>
        <p>
          You can browse without creating an account. When you request a page or
          image, hosting and security services may process your IP address,
          browser and device details, requested URL, and time of the request.
          These details help deliver the site, diagnose problems, and limit
          abusive traffic. Vercel handles the public website and its bot
          protection; Render runs the artwork backend. Cloudflare delivers
          private artwork storage to the backend. Neon hosts the backend
          database. These providers may keep operational and security records
          under their own policies.
        </p>
        <p>
          If you email me, your address and message reach my Gmail mailbox. I
          use them to reply and handle your request. Public visitors cannot
          upload artwork or open an account, and this site does not process
          purchases or payments.
          Staff sign-in uses security cookies and stores account and login
          security records, including records of failed sign-in attempts.
        </p>

        <h2>Browser storage and Clay Studio</h2>
        <p>
          The site saves your chosen light or dark theme in your browser. Clay
          Studio saves a design in your browser only when you select “Save
          design.” You can clear either through your browser’s site data
          controls. A Clay Studio share link puts the design in the link itself;
          anyone you share it with can read the design, and the URL may appear
          in request records when opened. Avoid putting private information in
          a shared design.
        </p>
        <p>
          Security checks may create a temporary browser session. The public
          site currently does not use advertising trackers or a separate
          audience analytics tool. If that changes, this policy will be
          updated and any required consent choices will be added.
        </p>

        <h2>Where information goes and how long it stays</h2>
        <p>
          Some infrastructure is hosted in the United States, including
          services in Northern Virginia. The providers above may process
          requests in other locations too. I keep correspondence for as long
          as needed to respond or maintain a relevant record. Provider logs,
          security records, and backups have their own retention periods. You
          can ask me about a particular record or request its deletion where
          applicable.
        </p>

        <h2>Links and your choices</h2>
        <p>
          Links to Instagram and kaancinar.com take you to other websites with
          their own privacy practices. You can choose not to email me, clear
          browser site data, or avoid sharing a Clay Studio link. To ask about
          information connected with you, request access or correction, or
          raise a privacy concern, email{" "}
          <a href="mailto:akcinar99@gmail.com">akcinar99@gmail.com</a>. I will
          review requests under the laws that apply.
        </p>
      </main>
      <GalleryFooter />
    </div>
  );
}
