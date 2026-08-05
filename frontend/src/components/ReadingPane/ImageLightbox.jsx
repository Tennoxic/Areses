export function ImageLightbox({ src, alt, onClose }) {
  if (!src) return null;
  return (
    <div className="lightbox-overlay" onClick={onClose}>
      <img className="lightbox-image" src={src} alt={alt || ""} onClick={(e) => e.stopPropagation()} />
    </div>
  );
}
