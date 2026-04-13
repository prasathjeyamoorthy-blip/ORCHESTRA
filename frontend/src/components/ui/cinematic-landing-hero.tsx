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
      className={cn("relative w-screen h-screen overflow-hidden flex items-center justify-center", className)}
      {...props}
    >
      {/* Text — top of screen, above robot */}
      <div className="absolute inset-x-0 top-0 z-0 flex flex-col items-center text-center pointer-events-none px-4 pt-10 sm:pt-14">
        <h1
          className="cin-line1 text-cinematic-glow text-6xl sm:text-7xl md:text-8xl lg:text-[9rem] font-black tracking-tight leading-none mb-1"
          style={{ fontFamily: 'Archivo, sans-serif' }}
        >
          {tagline1}
        </h1>
        <h1
          className="cin-line2 text-cinematic-accent text-6xl sm:text-7xl md:text-8xl lg:text-[9rem] font-black tracking-tight leading-none"
          style={{ fontFamily: 'Archivo, sans-serif' }}
        >
          {tagline2}
        </h1>
      </div>

      {/* Robot — z-10, on top of text */}
      {robotSlot && (
        <div className="absolute inset-0 z-10">
          {robotSlot}
        </div>
      )}

      {/* Get Started — z-20 */}
      {getStartedSlot && (
        <div className="absolute bottom-40 sm:bottom-44 inset-x-0 z-20 flex justify-center pointer-events-auto" style={{ paddingLeft: '65%' }}>
          {getStartedSlot}
        </div>
      )}
    </div>
  );
}
