"use client";

import { useTheme } from "next-themes";
import { useEffect, useRef, useSyncExternalStore } from "react";

interface Star {
  x: number;
  y: number;
  size: number;
  opacity: number;
}

interface ShootingStar {
  x: number;
  y: number;
  length: number;
  speed: number;
  angle: number;
  opacity: number;
  life: number;
  maxLife: number;
}

export function Starfield() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { resolvedTheme } = useTheme();
  const mounted = useSyncExternalStore(
    () => () => undefined,
    () => true,
    () => false
  );
  const isDark = !mounted || resolvedTheme !== "light";

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId: number;
    let stars: Star[] = [];
    let shootingStars: ShootingStar[] = [];
    let lastShootingStarTime = 0;

    function resize() {
      if (!canvas) return;
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx!.scale(dpr, dpr);
      initStars(rect.width, rect.height);
    }

    function initStars(w: number, h: number) {
      const count = Math.floor((w * h) / 3500);
      stars = Array.from({ length: count }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        size: Math.random() * 1.5 + 0.3,
        opacity: Math.random() * 0.6 + 0.2,
      }));
    }

    function spawnShootingStar() {
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const w = rect.width;
      const h = rect.height;

      shootingStars.push({
        x: Math.random() * w * 0.7,
        y: Math.random() * h * 0.35,
        length: Math.random() * 80 + 60,
        speed: Math.random() * 6 + 4,
        angle: Math.PI / 6 + Math.random() * (Math.PI / 6),
        opacity: 1,
        life: 0,
        maxLife: Math.random() * 40 + 30,
      });
    }

    function drawEarth(w: number, h: number) {
      if (!ctx) return;

      // Earth position: bottom-right area
      const ex = w * 0.82;
      const ey = h * 0.78;
      const radius = Math.min(w, h) * 0.045;

      // Earth glow
      const glowGrad = ctx.createRadialGradient(ex, ey, radius, ex, ey, radius * 3);
      glowGrad.addColorStop(0, "rgba(100, 180, 255, 0.12)");
      glowGrad.addColorStop(0.5, "rgba(100, 180, 255, 0.04)");
      glowGrad.addColorStop(1, "rgba(100, 180, 255, 0)");
      ctx.beginPath();
      ctx.arc(ex, ey, radius * 3, 0, Math.PI * 2);
      ctx.fillStyle = glowGrad;
      ctx.fill();

      // Earth body
      const earthGrad = ctx.createRadialGradient(
        ex - radius * 0.3,
        ey - radius * 0.3,
        0,
        ex,
        ey,
        radius
      );
      earthGrad.addColorStop(0, "#4da6ff");
      earthGrad.addColorStop(0.3, "#2d7bc4");
      earthGrad.addColorStop(0.6, "#1a5a8a");
      earthGrad.addColorStop(1, "#0d3b5e");
      ctx.beginPath();
      ctx.arc(ex, ey, radius, 0, Math.PI * 2);
      ctx.fillStyle = earthGrad;
      ctx.fill();

      // Continent hints (simplified land masses)
      ctx.save();
      ctx.beginPath();
      ctx.arc(ex, ey, radius, 0, Math.PI * 2);
      ctx.clip();

      ctx.fillStyle = "rgba(60, 140, 80, 0.5)";
      // Smaller continent blobs
      ctx.beginPath();
      ctx.ellipse(ex - radius * 0.2, ey - radius * 0.1, radius * 0.3, radius * 0.2, -0.3, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.ellipse(ex + radius * 0.3, ey + radius * 0.15, radius * 0.2, radius * 0.25, 0.4, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.ellipse(ex - radius * 0.1, ey + radius * 0.4, radius * 0.15, radius * 0.1, 0.2, 0, Math.PI * 2);
      ctx.fill();

      ctx.restore();

      // Atmosphere rim
      const atmosGrad = ctx.createRadialGradient(ex, ey, radius * 0.9, ex, ey, radius * 1.08);
      atmosGrad.addColorStop(0, "rgba(120, 200, 255, 0)");
      atmosGrad.addColorStop(0.5, "rgba(120, 200, 255, 0.15)");
      atmosGrad.addColorStop(1, "rgba(120, 200, 255, 0)");
      ctx.beginPath();
      ctx.arc(ex, ey, radius * 1.08, 0, Math.PI * 2);
      ctx.fillStyle = atmosGrad;
      ctx.fill();
    }

    function draw(time: number) {
      if (!canvas || !ctx) return;
      const rect = canvas.getBoundingClientRect();
      const w = rect.width;
      const h = rect.height;

      ctx.clearRect(0, 0, w, h);

      if (!isDark) {
        // Light mode — don't draw stars/earth on canvas
        animationId = requestAnimationFrame(draw);
        return;
      }

      // Draw static stars
      for (const star of stars) {
        ctx.beginPath();
        ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 255, 255, ${star.opacity})`;
        ctx.fill();
      }

      // Draw Earth
      drawEarth(w, h);

      // Spawn shooting stars (every 4-8 seconds)
      if (time - lastShootingStarTime > 4000 + Math.random() * 4000) {
        spawnShootingStar();
        lastShootingStarTime = time;
      }

      // Shooting stars
      for (let i = shootingStars.length - 1; i >= 0; i--) {
        const ss = shootingStars[i];
        ss.life++;
        ss.x += Math.cos(ss.angle) * ss.speed;
        ss.y += Math.sin(ss.angle) * ss.speed;

        const lifeRatio = ss.life / ss.maxLife;
        ss.opacity = lifeRatio < 0.1 ? lifeRatio / 0.1 : 1 - (lifeRatio - 0.1) / 0.9;

        if (ss.life >= ss.maxLife || ss.x > w + 100 || ss.y > h + 100) {
          shootingStars.splice(i, 1);
          continue;
        }

        const tailX = ss.x - Math.cos(ss.angle) * ss.length;
        const tailY = ss.y - Math.sin(ss.angle) * ss.length;

        const gradient = ctx.createLinearGradient(tailX, tailY, ss.x, ss.y);
        gradient.addColorStop(0, "rgba(255, 255, 255, 0)");
        gradient.addColorStop(0.7, `rgba(200, 200, 255, ${ss.opacity * 0.4})`);
        gradient.addColorStop(1, `rgba(255, 255, 255, ${ss.opacity * 0.9})`);

        ctx.beginPath();
        ctx.moveTo(tailX, tailY);
        ctx.lineTo(ss.x, ss.y);
        ctx.strokeStyle = gradient;
        ctx.lineWidth = 1.5;
        ctx.lineCap = "round";
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(ss.x, ss.y, 2, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 255, 255, ${ss.opacity})`;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(ss.x, ss.y, 5, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(180, 180, 255, ${ss.opacity * 0.25})`;
        ctx.fill();
      }

      animationId = requestAnimationFrame(draw);
    }

    resize();
    animationId = requestAnimationFrame(draw);
    window.addEventListener("resize", resize);

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener("resize", resize);
    };
  }, [isDark]);

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none absolute inset-0 h-full w-full"
      aria-hidden="true"
      style={{ opacity: isDark ? 1 : 0, transition: "opacity 0.8s ease" }}
    />
  );
}
