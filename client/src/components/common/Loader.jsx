import React from 'react';

export default function Loader({ size = 'md', fullScreen = false, text }) {
  const sizes = {
    sm: 'w-8 h-8 border-2',
    md: 'w-12 h-12 border-4',
    lg: 'w-16 h-16 border-4',
    xl: 'w-24 h-24 border-8',
  };

  const loader = (
    <div className="flex flex-col items-center justify-center gap-4">
      <div 
        className={`${sizes[size]} border-[#2c77d1] border-t-transparent rounded-full animate-spin`}
      />
      {text && <p className="text-gray-400">{text}</p>}
    </div>
  );

  if (fullScreen) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        {loader}
      </div>
    );
  }

  return loader;
}