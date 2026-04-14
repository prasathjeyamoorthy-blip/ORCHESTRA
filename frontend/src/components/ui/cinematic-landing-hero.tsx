"use client";
import React from "react";
import { cn } from "@/lib/utils";

export interface CinematicHeroProps extends React.HTMLAttributes<HTMLDivElement> {
  tagline1?: string;
  tagline2?: string;
  robotSlot?: React.ReactNode;
  getStartedSlot?: React.ReactNode;
}

export function CinematicHero({
  tagline1 = "Too many steps,",
  tagline2 = "made simple.",
  robotSlot,
  getStartedSlot,
  className,
  ...props
}: CinematicHeroProps) {
  return (
    <div
      className={cn("relative w-full min-h-[100svh] overflow-hidden flex items-center justify-center", className)}
      {...props}
    >
      {/* Text — top of screen */}
      <div className="absolute inset-x-0 top-0 z-0 flex flex-col items-center text-center pointer-events-none px-4 pt-8 sm:pt-12 md:pt-14">
        <h1
          className="cin-line1 text-cinematic-glow text-4xl sm:text-6xl md:text-8xl lg:text-[9rem] font-black tracking-tight leading-none mb-1"
          style={{ fontFamily: 'Archivo, sans-serif' }}
        >
          {tagline1}
        </h1>
        <h1
          className="cin-line2 text-cinematic-accent text-4xl sm:text-6xl md:text-8xl lg:text-[9rem] font-black tracking-tight leading-none"
          style={{ fontFamily: 'Archivo, sans-serif' }}
        >
          {tagline2}
        </h1>
      </div>

      {/* Robot — z-10 */}
      {robotSlot && (
        <div className="absolute inset-0 z-10">
          {robotSlot}
        </div>
      )}

      {/* Get Started — responsive positioning */}
      {getStartedSlot && (
        <div className="absolute z-20 pointer-events-auto
          bottom-16 right-6
          sm:bottom-32 sm:right-12
          md:bottom-40 md:right-[18%]
          lg:bottom-44 lg:right-[20%]">
          {getStartedSlot}
        </div>
      )}
    </div>
  );
}
