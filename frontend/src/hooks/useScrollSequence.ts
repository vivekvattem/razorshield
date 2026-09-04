import { useEffect, useRef, useState } from "react";

export function useScrollSequence(totalStages: number) {
  const ref = useRef<HTMLElement>(null);
  const triggered = useRef(false);
  const [started, setStarted] = useState(false);
  const [activeStage, setActiveStage] = useState(0);

  useEffect(() => {
    const target = ref.current;
    if (!target) return;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (reduceMotion.matches) {
      triggered.current = true;
      setStarted(true);
      setActiveStage(totalStages);
      return;
    }
    let timers: number[] = [];
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting || triggered.current) return;
        triggered.current = true;
        setStarted(true);
        setActiveStage(1);
        timers = Array.from({ length: totalStages - 1 }, (_, index) =>
          window.setTimeout(() => setActiveStage(index + 2), 560 * (index + 1)),
        );
        observer.disconnect();
      },
      { threshold: 0.28 },
    );
    observer.observe(target);
    return () => {
      observer.disconnect();
      timers.forEach(window.clearTimeout);
    };
  }, [totalStages]);

  return { ref, started, activeStage };
}
