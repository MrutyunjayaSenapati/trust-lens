"use client";
import { useEffect } from "react";

/** Registers the service worker and stashes the browser's install prompt so the header button can use it. */
export default function PwaClient() {
  useEffect(() => {
    if ("serviceWorker" in navigator && window.location.protocol !== "file:") {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    }
    const onPrompt = (e: Event) => {
      e.preventDefault();
      (window as any).__tlInstall = e;
      window.dispatchEvent(new Event("tl-installable"));
    };
    const onInstalled = () => {
      (window as any).__tlInstall = null;
      window.dispatchEvent(new Event("tl-installed"));
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", onPrompt);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);
  return null;
}
