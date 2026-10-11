import { LoadingRegion, Skeleton } from "@/components/ui/feedback";

export default function Loading() {
  return (
    <LoadingRegion className="flex flex-col gap-6">
      <Skeleton className="h-10 w-56" />
      <Skeleton className="h-40" />
      <Skeleton className="h-64" />
    </LoadingRegion>
  );
}
