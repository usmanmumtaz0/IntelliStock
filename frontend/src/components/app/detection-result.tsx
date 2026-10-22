import type { VideoDetectionDto } from "@/lib/api";
import { Tag } from "@/components/app/primitives";

export function DetectionResult({ detection }: { detection: VideoDetectionDto }) {
  const evidence = detection.identity_evidence ?? {};
  const identified = detection.identity_status === "identified" && Boolean(detection.product_id);
  const name = identified
    ? typeof evidence["catalog_name"] === "string"
      ? evidence["catalog_name"]
      : detection.class_name
    : "Product needs review";
  const tokens = Array.isArray(evidence["ocr_tokens"])
    ? evidence["ocr_tokens"].filter((token): token is string => typeof token === "string")
    : [];
  const description =
    typeof evidence["florence_description"] === "string" ? evidence["florence_description"] : "";
  const errors = Array.isArray(evidence["provider_errors"])
    ? evidence["provider_errors"].filter((error): error is string => typeof error === "string")
    : [];
  return (
    <section className="mt-3 space-y-3 rounded-lg border bg-background p-3 text-xs">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="break-words text-sm font-semibold">{name}</h3>
        <Tag tone={identified ? "healthy" : "warning"}>
          {identified ? "Identified" : "Needs review"}
        </Tag>
      </div>
      <p className="text-muted-foreground">
        {[detection.brand, detection.variant, detection.package_size].filter(Boolean).join(" / ") ||
          detection.category ||
          "Product observation"}
      </p>
      <dl className="space-y-2">
        <div>
          <dt className="font-medium">YOLO prediction</dt>
          <dd className="break-words text-muted-foreground">
            {detection.class_name} - {Math.round(detection.confidence * 100)}%
          </dd>
        </div>
        <div>
          <dt className="font-medium">Text read from packaging</dt>
          <dd className="break-words text-muted-foreground">
            {tokens.length
              ? tokens.join(" / ")
              : errors.includes("ocr_unavailable")
                ? "OCR was unavailable for this result."
                : "No readable text recorded."}
          </dd>
        </div>
        <div>
          <dt className="font-medium">Florence description (supporting evidence)</dt>
          <dd className="break-words text-muted-foreground">
            {description ||
              (errors.includes("florence_unavailable")
                ? "Florence was unavailable for this result."
                : "No Florence description recorded for this result.")}
          </dd>
        </div>
        <div>
          <dt className="font-medium">Identity evidence score</dt>
          <dd className="text-muted-foreground">
            {Math.round(detection.identity_confidence * 100)}% - Evidence strength, not a
            probability of correctness.
          </dd>
        </div>
      </dl>
      {typeof evidence["method"] === "string" && (
        <p className="text-muted-foreground">
          Matched using: {evidence["method"].replaceAll("_", " ")}
        </p>
      )}
      {detection.track_id !== null && (
        <p className="text-muted-foreground">Track #{detection.track_id}</p>
      )}
    </section>
  );
}
