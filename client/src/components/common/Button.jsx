import React from 'react';

export default function Button({ 
  children, 
  variant = 'primary', 
  size = 'md', 
  fullWidth = false,
  disabled = false,
  onClick,
  type = 'button',
  className = '',
  icon: Icon,
  iconPosition = 'left',
}) {
  const baseStyles = 'font-semibold rounded-full transition flex items-center justify-center gap-2';
  
  const variants = {
    primary: 'bg-gradient-to-r from-[#2c77d1] to-[#9426f4] hover:opacity-90 text-white',
    secondary: 'border-2 border-[#2c77d1] text-[#2c77d1] hover:bg-[#2c77d1]/10',
    outline: 'border border-[#2c77d1]/30 hover:border-[#2c77d1] text-white',
    ghost: 'text-[#2c77d1] hover:bg-[#2c77d1]/10',
    danger: 'bg-red-500 hover:bg-red-600 text-white',
  };

  const sizes = {
    sm: 'px-4 py-2 text-sm',
    md: 'px-6 py-3 text-base',
    lg: 'px-8 py-4 text-lg',
  };

  const widthClass = fullWidth ? 'w-full' : '';
  const disabledClass = disabled ? 'opacity-50 cursor-not-allowed' : '';

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${widthClass} ${disabledClass} ${className}`}
    >
      {Icon && iconPosition === 'left' && <Icon className="w-5 h-5" />}
      {children}
      {Icon && iconPosition === 'right' && <Icon className="w-5 h-5" />}
    </button>
  );
}