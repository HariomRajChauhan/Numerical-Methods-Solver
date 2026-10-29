import { Icon } from "./Icon";

interface BrandMarkProps {
  className?: string;
  iconSize?: number;
}

/** Shared gradient sigma mark used in the header, footer and print header. */
export function BrandMark({ className = "h-9 w-9", iconSize = 19 }: BrandMarkProps) {
  return (
    <span
      aria-hidden="true"
      className={`relative inline-flex shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-lg shadow-indigo-500/30 ${className}`}
    >
      <Icon name="sigma" size={iconSize} strokeWidth={2.1} />
    </span>
  );
}
