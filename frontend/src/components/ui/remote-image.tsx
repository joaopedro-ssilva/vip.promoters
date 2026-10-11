"use client";

import { Image as ImageIcon } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/cn";
import { safeUrl } from "@/lib/safe-url";

/**
 * Remote images (Instagram posts, reward pictures) are arbitrary, expiring CDN
 * URLs, so they are rendered with a plain lazy <img> (never next/image) inside
 * a fixed aspect-ratio box. On error (or an unsafe URL) a neutral fallback is shown.
 */
export function RemoteImage({
  src,
  alt = "",
  ratio = "aspect-[4/3]",
  fallbackLabel = "Publicação",
  fallbackIcon: FallbackIcon = ImageIcon,
  className,
}: {
  src: string | null | undefined;
  alt?: string;
  ratio?: string;
  fallbackLabel?: string;
  fallbackIcon?: typeof ImageIcon;
  className?: string;
}) {
  const safe = safeUrl(src);
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const failed = !safe || failedSrc === safe;
  return (
    <div className={cn("relative w-full overflow-hidden rounded-control bg-surface-raised", ratio, className)}>
      {failed ? (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-1 p-2 text-center text-caption text-ink-muted">
          <FallbackIcon aria-hidden="true" strokeWidth={1.75} className="size-6" />
          <span>{fallbackLabel}</span>
        </div>
      ) : (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={safe}
          alt={alt}
          loading="lazy"
          decoding="async"
          referrerPolicy="no-referrer"
          onError={() => setFailedSrc(safe)}
          className="absolute inset-0 size-full object-cover"
        />
      )}
    </div>
  );
}
