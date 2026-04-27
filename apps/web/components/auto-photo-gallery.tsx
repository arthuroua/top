"use client";

import { useEffect, useState } from "react";

type AutoPhotoGalleryProps = {
  images: string[];
  vehicleName: string;
};

export function AutoPhotoGallery({ images, vehicleName }: AutoPhotoGalleryProps) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const activeImage = activeIndex === null ? null : images[activeIndex];
  const featuredThumbs = images.slice(1, 5);
  const restThumbs = images.slice(5);

  const showPrevious = () => setActiveIndex((current) => Math.max(0, (current || 0) - 1));
  const showNext = () => setActiveIndex((current) => Math.min(images.length - 1, (current || 0) + 1));

  useEffect(() => {
    if (activeIndex === null) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setActiveIndex(null);
      if (event.key === "ArrowRight") setActiveIndex((current) => (current === null ? 0 : Math.min(images.length - 1, current + 1)));
      if (event.key === "ArrowLeft") setActiveIndex((current) => (current === null ? 0 : Math.max(0, current - 1)));
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [activeIndex, images.length]);

  if (images.length === 0) return null;

  return (
    <>
      <div className={`autoTopGallery ${images.length === 1 ? "autoTopGallerySingle" : ""}`}>
        <button type="button" className="autoTopMainPhoto" onClick={() => setActiveIndex(0)}>
          <img src={images[0]} alt={`${vehicleName} main auction photo`} loading="eager" />
        </button>
        {featuredThumbs.length > 0 && (
          <div className="autoTopThumbs">
            {featuredThumbs.map((url, imageIndex) => (
              <button key={`${url}-top-${imageIndex}`} type="button" onClick={() => setActiveIndex(imageIndex + 1)}>
                <img src={url} alt={`${vehicleName} auction photo ${imageIndex + 2}`} loading="lazy" />
              </button>
            ))}
          </div>
        )}
        {restThumbs.length > 0 && (
          <div className="autoTopMoreThumbs" aria-label={`${vehicleName} more auction photos`}>
            {restThumbs.map((url, imageIndex) => {
              const realIndex = imageIndex + 5;
              return (
                <button key={`${url}-more-${imageIndex}`} type="button" onClick={() => setActiveIndex(realIndex)}>
                  <img src={url} alt={`${vehicleName} auction photo ${realIndex + 1}`} loading="lazy" />
                </button>
              );
            })}
          </div>
        )}
      </div>

      {activeImage && (
        <div className="photoLightbox" role="dialog" aria-modal="true" aria-label={`${vehicleName} photo preview`}>
          <button type="button" className="photoLightboxBackdrop" aria-label="Close photo" onClick={() => setActiveIndex(null)} />
          <div className="photoLightboxPanel">
            <button type="button" className="photoLightboxClose" onClick={() => setActiveIndex(null)}>
              X
            </button>
            {images.length > 1 && (
              <>
                <button type="button" className="photoLightboxArrow photoLightboxArrowPrev" onClick={showPrevious} aria-label="Previous photo">
                  ‹
                </button>
                <button type="button" className="photoLightboxArrow photoLightboxArrowNext" onClick={showNext} aria-label="Next photo">
                  ›
                </button>
              </>
            )}
            <img src={activeImage} alt={`${vehicleName} auction photo preview`} />
            {images.length > 1 && (
              <div className="photoLightboxNav">
                <button type="button" onClick={showPrevious}>
                  Prev
                </button>
                <span>
                  {(activeIndex || 0) + 1} / {images.length}
                </span>
                <button type="button" onClick={showNext}>
                  Next
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
