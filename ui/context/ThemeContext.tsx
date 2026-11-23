"use client";

import React, { createContext, useContext, useEffect, useState } from "react";

type Theme = "dark" | "light";

interface ThemeContextType {
  theme: Theme;
  toggleTheme: (event?: React.MouseEvent) => void;
  setTheme: (t: Theme, event?: React.MouseEvent) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("dark");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("incidentiq_theme") as Theme | null;
    const initial = saved || "dark";
    setThemeState(initial);
    applyTheme(initial);
    setMounted(true);
  }, []);

  const applyTheme = (t: Theme) => {
    const root = document.documentElement;
    const body = document.body;
    if (t === "dark") {
      root.classList.add("dark");
      root.classList.remove("light");
      root.style.colorScheme = "dark";
      body.classList.add("dark");
      body.classList.remove("light");
    } else {
      root.classList.remove("dark");
      root.classList.add("light");
      root.style.colorScheme = "light";
      body.classList.remove("dark");
      body.classList.add("light");
    }
  };

  const setThemeWithRipple = (newTheme: Theme, event?: React.MouseEvent) => {
    // Check if View Transitions API is supported
    const doc = document as any;
    if (!doc.startViewTransition || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setThemeState(newTheme);
      localStorage.setItem("incidentiq_theme", newTheme);
      applyTheme(newTheme);
      return;
    }

    // Get origin coordinates of click
    const x = event?.clientX ?? window.innerWidth / 2;
    const y = event?.clientY ?? window.innerHeight / 2;
    const endRadius = Math.hypot(
      Math.max(x, window.innerWidth - x),
      Math.max(y, window.innerHeight - y)
    );

    const transition = doc.startViewTransition(() => {
      setThemeState(newTheme);
      localStorage.setItem("incidentiq_theme", newTheme);
      applyTheme(newTheme);
    });

    transition.ready.then(() => {
      document.documentElement.animate(
        {
          clipPath: [
            `circle(0px at ${x}px ${y}px)`,
            `circle(${endRadius}px at ${x}px ${y}px)`,
          ],
        },
        {
          duration: 450,
          easing: "cubic-bezier(0.4, 0, 0.2, 1)",
          pseudoElement: "::view-transition-new(root)",
        }
      );
    });
  };

  const toggleTheme = (event?: React.MouseEvent) => {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setThemeWithRipple(nextTheme, event);
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme: setThemeWithRipple }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
}
