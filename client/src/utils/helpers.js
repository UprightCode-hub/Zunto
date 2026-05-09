export const formatNaira = (value, options = {}) => {
  const {
    fallback = 'Price unavailable',
    minimumFractionDigits = 0,
    maximumFractionDigits = 0,
  } = options;

  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return fallback;
  }

  return `₦${numericValue.toLocaleString('en-NG', {
    minimumFractionDigits,
    maximumFractionDigits,
  })}`;
};

export const formatConditionLabel = (condition) => {
  const value = String(condition || '').trim().toLowerCase();
  if (!value) return 'N/A';

  const labels = {
    new: 'New',
    like_new: 'Used - Like New',
    good: 'Used - Good',
    fair: 'Used - Fair',
    poor: 'Used - Poor',
  };

  return labels[value] || value.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
};
