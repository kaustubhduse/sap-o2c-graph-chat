import { useState, useRef } from 'react';

export default function DraggableOverlay({ children, initialPosition = { x: window.innerWidth * 0.1, y: 100 } }) {
  const [position, setPosition] = useState(initialPosition);
  const [isDragging, setIsDragging] = useState(false);
  const dragOffset = useRef({ x: 0, y: 0 });

  const handlePointerDown = (e) => {
    // Prevent drag initiation from buttons, links, or scrollable content areas
    if (e.target.closest('button') || e.target.closest('a') || e.target.closest('.overflow-y-auto')) {
      return; 
    }
    
    setIsDragging(true);
    dragOffset.current = {
      x: e.clientX - position.x,
      y: e.clientY - position.y
    };
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e) => {
    if (!isDragging) return;
    setPosition({
      x: e.clientX - dragOffset.current.x,
      y: e.clientY - dragOffset.current.y
    });
  };

  const handlePointerUp = (e) => {
    setIsDragging(false);
    e.currentTarget.releasePointerCapture(e.pointerId);
  };

  return (
    <div
      className="absolute top-0 left-0 z-40 shadow-2xl rounded-xl bg-surface-900 border border-surface-700 max-h-[70vh] flex flex-col will-change-transform"
      style={{ 
        transform: `translate(${position.x}px, ${position.y}px)`,
        cursor: isDragging ? 'grabbing' : 'grab',
        touchAction: 'none'
      }}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
    >
      {children}
    </div>
  );
}
