"use client";

import { useLayoutEffect, useRef, type TouchEvent as ReactTouchEvent } from "react";
import { flushSync } from "react-dom";
import ArtworkThumbnail from "@/components/ArtworkThumbnail";

export type GalleryImage = {
  id: number;
  src: string;
  viewerSrc: string;
  alt: string;
};

export default function ArtworkPhotoCarousel({
  images,
  index,
  onNavigate,
  className,
  fullSize = false,
}: {
  images: GalleryImage[];
  index: number;
  onNavigate: (direction: number) => void;
  className: string;
  fullSize?: boolean;
}) {
  const surface = useRef<HTMLDivElement>(null);
  const track = useRef<HTMLDivElement>(null);
  const animation = useRef<Animation | null>(null);
  const swipe = useRef<{
    identifier: number;
    x: number;
    y: number;
    time: number;
    width: number;
    offset: number;
    axis?: "horizontal" | "vertical";
  } | null>(null);
  const canSwipe = images.length > 1;
  const selected = images[index];
  const indexAt = (offset: number) => (index + offset + images.length) % images.length;

  function resetTrack() {
    animation.current?.cancel();
    animation.current = null;
    swipe.current = null;
    track.current?.style.removeProperty("transform");
  }

  useLayoutEffect(() => {
    const strip = track.current;
    return () => {
      animation.current?.cancel();
      animation.current = null;
      swipe.current = null;
      strip?.style.removeProperty("transform");
    };
  }, [index]);

  function navigate(direction: number) {
    resetTrack();
    if (direction !== 0) onNavigate(direction);
  }

  useLayoutEffect(() => {
    const element = surface.current;
    if (!canSwipe || !element) return;

    function moveSwipe(event: TouchEvent) {
      const gesture = swipe.current;
      const touch = event.touches[0];
      if (!gesture || touch?.identifier !== gesture.identifier || !track.current) return;
      const x = touch.clientX - gesture.x;
      const y = touch.clientY - gesture.y;

      if (!gesture.axis && Math.max(Math.abs(x), Math.abs(y)) >= 6) {
        gesture.axis = Math.abs(x) > Math.abs(y) ? "horizontal" : "vertical";
      }
      if (gesture.axis !== "horizontal" || !event.cancelable) return;

      // Claim the gesture before the browser starts scrolling on diagonal drags.
      event.preventDefault();
      gesture.offset = Math.max(-gesture.width, Math.min(gesture.width, x));
      track.current.style.transform = `translateX(${gesture.offset}px)`;
    }

    element.addEventListener("touchmove", moveSwipe, { passive: false });
    return () => element.removeEventListener("touchmove", moveSwipe);
  }, [canSwipe]);

  function finishSwipe(event: ReactTouchEvent<HTMLDivElement>, cancelled = false) {
    const gesture = swipe.current;
    const strip = track.current;
    if (!gesture || !strip || !Array.from(event.changedTouches).some(
      (touch) => touch.identifier === gesture.identifier,
    )) return;
    swipe.current = null;
    if (gesture.offset === 0) return;

    const distance = Math.abs(gesture.offset);
    const duration = Math.max(1, event.timeStamp - gesture.time);
    const flick = distance >= 28 && distance / duration >= 0.45;
    const advance = !cancelled && (flick || distance >= gesture.width * 0.22);
    const direction = advance ? -Math.sign(gesture.offset) : 0;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      navigate(direction);
      return;
    }

    const settling = strip.animate(
      [
        { transform: `translateX(${gesture.offset}px)` },
        { transform: `translateX(${-direction * gesture.width}px)` },
      ],
      { duration: 240, easing: "cubic-bezier(0.2, 0.8, 0.2, 1)", fill: "forwards" },
    );
    animation.current = settling;
    settling.onfinish = () => {
      // Swap the centered slide before removing the animation's final transform.
      flushSync(() => navigate(direction));
    };
  }

  return (
    <div
      className={`${className}${canSwipe ? " is-swipeable" : ""}`}
      ref={surface}
      onTouchStart={(event) => {
        if (!canSwipe) return;
        if (event.touches.length !== 1) {
          if (swipe.current) resetTrack();
          return;
        }
        if (animation.current) return;
        const touch = event.touches[0];
        swipe.current = {
          identifier: touch.identifier,
          x: touch.clientX,
          y: touch.clientY,
          time: event.timeStamp,
          width: event.currentTarget.clientWidth,
          offset: 0,
        };
      }}
      onTouchCancel={(event) => finishSwipe(event, true)}
      onTouchEnd={(event) => finishSwipe(event)}
    >
      {selected ? (
        <div className="artwork-photo-track" ref={track}>
          {(canSwipe ? [-1, 0, 1] : [0]).map((offset) => {
            const photo = images[indexAt(offset)];
            const current = offset === 0;
            return (
              <div
                key={offset}
                className="artwork-photo-slide"
                data-current={current}
                aria-hidden={current ? undefined : true}
                style={{ left: `${offset * 100}%` }}
              >
                <ArtworkThumbnail
                  key={photo.src}
                  src={photo.src}
                  alt={current && (!fullSize || photo.viewerSrc === photo.src) ? photo.alt : ""}
                  priority={current && !fullSize}
                  eager
                  draggable={false}
                />
                {current && fullSize && photo.viewerSrc !== photo.src && (
                  <ArtworkThumbnail
                    key={photo.viewerSrc}
                    src={photo.viewerSrc}
                    alt={photo.alt}
                    eager
                    draggable={false}
                  />
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <span>Image unavailable</span>
      )}
    </div>
  );
}
