import React from 'react';

export default function Card({ 
  children, 
  className = '', 
  hover = false,
  padding = 'md',
}) {
  const paddings = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  };

  const hoverClass = hover ? 'hover:border-[#2c77d1] transition cursor-pointer' : '';

  return (
    <div 
      className={`bg-[#050d1b] border border-[#2c77d1]/20 rounded-2xl ${paddings[padding]} ${hoverClass} ${className}`}
    >
      {children}
    </div>
  );
}